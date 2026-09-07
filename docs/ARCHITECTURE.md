# Architecture

This document explains how helsinki-rag-gcp answers a question end to end,
what each moving part does, and how the pieces map onto GCP resources when
deployed. It is meant to be read start to finish once, then used as a
reference.

## What the service does

The service answers natural-language questions about Helsinki public
service points (libraries, daycares, health stations, and similar) from a
fixed corpus of over 21,498 rows (`data/helsinki_service_points.csv`). It
is a single FastAPI application with one real endpoint, `POST /ask`, plus
a health check and a built-in browser UI.

Every answer is grounded in retrieved passages and cites them by id, so a
caller can verify a claim against the exact source row rather than trust
free text. If nothing relevant is retrieved, the service says so instead
of guessing.

The whole stack runs two ways from the same source code:

- **Local / offline**: every adapter is a small in-process implementation
  with no network calls. This is what runs in tests, in `make eval`, and
  under `make run`.
- **Cloud / GCP**: each adapter is swapped for a call to a managed GCP
  service (Vertex AI Search, Gemini, Model Armor, BigQuery), selected
  purely by environment variables. No code changes between the two.

## Request path for one question

```
 client (web UI, curl, voice channel)
        |
        |  POST /ask {question, language, channel}
        v
 +---------------------------------------------------------+
 | FastAPI app (src/hrag/api.py)                            |
 |                                                           |
 |  1. guard.check(question)          budget   50 ms         |
 |       |                                                   |
 |       +-- blocked? --> log turn (outcome=blocked)         |
 |       |                --> HTTP 400 {detail: reason}      |
 |       v allowed                                           |
 |  2. retriever.search(question, k=5)  budget  150 ms       |
 |       v passages (ranked, with score)                     |
 |  3. generator.generate(question, passages) budget 800 ms  |
 |       v answer text with [id] citations + no_answer flag  |
 |  4. turnlog.write(turn)              async, no budget     |
 |       v                                                   |
 |  return AskResponse (answer, citations, model, no_answer, |
 |         latency_ms, passages, guard)                      |
 +---------------------------------------------------------+
        |
        v
 client renders answer, passage cards, latency bar, guard state
```

Every stage is timed with a monotonic clock and reported back in
`latency_ms`. Per `docs/LATENCY.md`, the budgets are:

| Stage    | Budget  | Notes                                            |
|----------|---------|---------------------------------------------------|
| guard    | 50 ms   | Model Armor call in the cloud; near 0 ms locally   |
| retrieve | 150 ms  | Vertex AI Search query, top-k passages             |
| generate | 800 ms  | Includes a 400 ms first-token sub-budget           |
| log      | async   | Not on the critical path, not counted toward total |

`log` runs after the response is already assembled, so the latency the
caller actually experiences is `guard + retrieve + generate`, target
under 1.5 seconds, not the `total` key (which also includes `log`).

### Guard runs before retrieval

The guard check is the very first thing that happens, before any passage
is read or any text reaches a model. A blocked question never touches the
retriever or the generator, and the turn is still logged (with
`outcome="blocked"` and no passage/citation data) so blocked traffic is
visible without ever storing what was blocked.

### Citations and the eval gate

Both generators (`TemplateGenerator`, `GeminiGenerator`) tag every fact
with the id of the passage it came from, e.g. `[8215]`. `GeminiGenerator`
goes one step further and drops any cited id that was not actually in the
retrieved set. A model cannot cite a passage it was never shown. This is
what `citation_ok` in the eval gate checks (see below).

## The adapter pattern

Four capabilities are defined as `Protocol`s in `src/hrag/ports.py`:
`Retriever`, `Generator`, `Guard`, `TurnLog`. The API and the eval harness
depend only on these interfaces, never on a concrete class, so a local and
a cloud implementation are interchangeable without touching call sites.

`src/hrag/config.py` reads four environment variables to decide which
concrete class backs each port:

- `HRAG_RETRIEVER` (default `local`): `LocalRetriever`, or
  `VertexSearchRetriever` when set to `vertex`.
- `HRAG_GENERATOR` (default `template`): `TemplateGenerator`, or
  `GeminiGenerator` when set to `gemini`.
- `HRAG_GUARD` (default `heuristic`): `HeuristicGuard`, or
  `ModelArmorGuard` when set to `model_armor`.
- `HRAG_TURNLOG` (default `jsonl`): `JsonlTurnLog`, or `BigQueryTurnLog`
  when set to `bigquery`.

`build_adapters()` also records which kind was chosen for each port in an
`Adapters.names` dict; `GET /healthz` returns this, and the UI's footer
reads it to show which adapters are live.

Each cloud adapter reads its own extra configuration from the environment
and creates its GCP client lazily (on first use, not at import time), so
importing the module never requires network access or the `gcp` extra to
be installed:

- `HRAG_MODEL_ARMOR_TEMPLATE` (default `""`), used by `ModelArmorGuard`:
  the Model Armor template resource name to call.
- `HRAG_GEMINI_MODEL` (default `gemini-2.5-flash`), used by
  `GeminiGenerator`: which Gemini model to prompt.
- `HRAG_VERTEX_SERVING_CONFIG` (default `""`), used by
  `VertexSearchRetriever`: the Vertex AI Search serving config path.
- `HRAG_BQ_TABLE` (default `""`), used by `BigQueryTurnLog`: the fully
  qualified BigQuery table to insert turns into.

The Cloud Run deployment (`infra/terraform/main.tf`) sets all eight of
these variables so a deployed service always runs the cloud adapters;
locally, none of them need to be set at all.

## Data model (`src/hrag/ports.py`)

- **`Passage`**: one retrieved source row (`id`, `title`, `text`,
  `source_url`, `score`). Both retrievers produce these; the generators and
  the API only ever see `Passage` objects, never raw CSV rows or raw
  Vertex AI Search results.
- **`GuardResult`**: `allowed` (bool) and `reason` (string, empty when
  allowed). Both guard adapters return the same shape regardless of how
  they decided.
- **`Answer`**: `text`, `citations` (tuple of passage ids actually cited),
  `model` (which generator/model produced it), `no_answer` (true when no
  passages were retrieved at all).
- **`Turn`**: one logged request. Carries `turn_id`, `channel`,
  `language`, `question_hash`, `passage_ids`, `cited_ids`, `model`,
  `guard`, `latency_ms`, `outcome`, and deliberately never the question
  text itself (see Security notes).

## The content pipeline

`scripts/ingest_to_jsonl.py` converts the source CSV into the JSONL format
Vertex AI Search expects for a custom "unstructured with metadata" data
store: one JSON document per line, with an `id`, a `structData` object
(the structured, filterable fields: name, address, provider type, phone,
url) and a base64-encoded plain-text `content` block (the same fields
rendered as prose, which is what full-text search actually matches
against). It streams the CSV row by row rather than loading it into
memory, capped at `MAX_ROWS = 50_000` rows as a bound on a single run.

The output of this script is what gets imported into the
`google_discovery_engine_data_store` resource described below. This
script is not run automatically by any Make target; it is a one-off (or
occasionally re-run) step ahead of a real deployment.

## The eval gate

`eval/run.py` is what `make eval` runs. It always retrieves against
`LocalRetriever` (so the gate works with no network and no GCP project),
and generates against `TemplateGenerator` if it is importable, skipping
generation-based checks otherwise. For each question in
`eval/golden.jsonl` it:

- retrieves the top `K = 5` passages and checks whether any of the row ids
  in the case's `expect_any` list was retrieved (`hit_at_5`);
- generates an answer and checks that every id it cites is a subset of
  the ids that were actually retrieved (`citation_ok`);
- records retrieval latency to report `p50`/`p95` (informational only,
  not gated).

Two thresholds fail the run: `hit_at_5 >= 0.8` and `citation_ok >= 1.0`.
`gate_failed()` returns true if either is breached, and `main()` exits
with status 1 in that case. That is what makes this a CI gate rather
than a report: a regression in retrieval quality or a generator that
invents a citation both fail the build.

## Infrastructure (`infra/terraform/`)

One line per resource in `main.tf`:

- `google_project_service.apis`: enables the seven GCP APIs the stack
  needs (Cloud Run, Discovery Engine, Vertex AI, BigQuery, Artifact
  Registry, Cloud Build, Model Armor).
- `google_artifact_registry_repository.hrag`: Docker repo the deployed
  container image is pushed to and pulled from.
- `google_service_account.hrag`: the dedicated runtime identity for the
  Cloud Run service (`hrag-api`), not the default compute service account.
- `google_project_iam_member.hrag_sa_roles`: grants that service account
  exactly four roles (`discoveryengine.viewer`, `aiplatform.user`,
  `bigquery.dataEditor`, `logging.logWriter`), for read-only search,
  model invocation, write-only turn logging, and log writes, nothing
  broader.
- `google_cloud_run_v2_service.hrag`: the deployed API container, with
  the eight `HRAG_*` env vars set to the cloud adapter values, scaling
  bounds, and concurrency from `variables.tf`.
- `google_discovery_engine_data_store.hrag`: the Vertex AI Search corpus
  the ingested JSONL is imported into.
- `google_discovery_engine_search_engine.hrag`: the search engine/serving
  config layered on top of that data store, with the LLM search add-on
  enabled.
- `google_bigquery_dataset.hrag` + `google_bigquery_table.turns`: the
  turn log's dataset and table; the table schema mirrors the `Turn`
  dataclass field for field, plus an extra `ts` timestamp column the
  application itself does not set.

`deploy.sh` (run by hand, not by CI) does three things in order:

1. `gcloud builds submit --tag <image> .` builds the container on Cloud
   Build and pushes it to Artifact Registry.
2. `terraform apply -var project=... -var region=... -var image=...`
   applies the module above with that freshly built image.
3. Reads the `service_url` Terraform output and prints it.

## Security notes

- **No citizen text in the turn table.** `Turn` never carries the raw
  question, only `question_hash` (a SHA-256 hex digest computed in
  `api.py` before anything else happens). Both turn-log adapters persist
  whatever is on the `Turn` object, so this guarantee lives in the shared
  data model, not in either adapter.
- **The guard runs before retrieval or generation.** A blocked question
  never reaches the corpus or a model call; only its hash and the block
  reason are logged.
- **Retrieved text is treated as data, not instructions.** The generator
  prompt (see `SYSTEM_PROMPT` in `generator.py`) wraps each passage in an
  explicit `<passage id="...">...</passage>` tag and instructs the model
  to answer only from those passages, citing ids. The retrieved rows are
  never concatenated into the instruction text itself.
- **Guard failure is fail-closed.** `ModelArmorGuard` treats any transport
  or API error as a block rather than letting an unsanitized question
  through when the check itself is unavailable.
- **Least-privilege service account.** The Cloud Run identity holds
  exactly the four IAM roles listed above, no project-wide editor role,
  no access to resources this service does not use.

## Running it locally

```
make setup   # uv sync
make test    # all adapters mocked/local
make eval    # golden-set gate against LocalRetriever + TemplateGenerator
make run     # starts the API on :8080 with local adapters
```

No environment variables are required for any of the above. The four
`HRAG_*` selector variables default to the local adapters.

## Running the UI

`make run`, then open `http://localhost:8080/` in a browser. The page is
a single static HTML file (`src/hrag/static/index.html`) with inline CSS
and vanilla JavaScript (no build step, no external CDN), so it works with
no network access. It offers three example questions (one library, one
daycare, one health station), lets you pick a language and channel, and
on submit calls `POST /ask` and renders the answer with citations
highlighted, a latency bar per stage against the budgets above, the
retrieved passages as cards, the guard decision, and the active model
name. A blocked (400) question is shown in red with the guard's reason.

## Running the eval

```
make eval
```

Prints a small table (`hit_at_5`, `citation_ok`, `p50`/`p95` latency) and
exits non-zero if either threshold is breached. This is the same command
CI runs, so a failing eval locally means CI will fail too.

## What the local twins do not prove

Running everything locally is convenient and is what CI actually
exercises, but it does not validate:

- **Real Vertex AI Search ranking quality.** `LocalRetriever` does plain
  keyword substring scoring with no stemming, no synonym handling, and
  no semantic matching. `hit_at_5=1.00` on the golden set says this
  scorer works for those specific questions, not that Vertex AI Search
  will rank the same way.
- **Model Armor's actual policy behavior.** `HeuristicGuard` matches a
  short fixed phrase list and a character-count limit; it does not
  exercise Model Armor's real prompt-injection or jailbreak detection
  models at all.
- **Network latency.** Every local adapter runs in-process with no RPC,
  no TLS handshake, and no regional round trip. The `retrieve`/`generate`
  latency numbers `make eval` reports are not representative of a Cloud
  Run instance calling Vertex AI Search and Gemini over the network.
- **Cold starts and concurrency.** `min_instances = 0` by default means a
  real deployment can scale to zero and pay a cold-start cost that no
  local run ever sees.

## How to extend

- **A new channel adapter** (e.g. a phone/IVR front end instead of the
  web UI): add a new caller of `POST /ask` that sets `channel` to
  something other than `"web"`/`"voice"` and translates its own input
  format to `{question, language, channel}`. Nothing in the API needs to
  change; `channel` is stored as free text on the `Turn`.
- **A new retriever**: implement the `Retriever` protocol
  (`search(query, k) -> list[Passage]`) in a new module, add a branch in
  `config.py`'s `build_adapters()` keyed on a new `HRAG_RETRIEVER` value,
  and add an offline-friendly fake for it in tests, following the pattern
  `retrieval/local.py` and `retrieval/vertex.py` already establish.
- **A new corpus**: point `LocalRetriever`/`scripts/ingest_to_jsonl.py` at
  a different CSV with the same column shape, or extend
  `build_document()`/`render_text()` if the new corpus has different
  fields, then re-run the ingest script and re-import into the Vertex AI
  Search data store. The golden set in `eval/golden.jsonl` will need new
  cases matching the new corpus's rows before the eval gate means
  anything again.
