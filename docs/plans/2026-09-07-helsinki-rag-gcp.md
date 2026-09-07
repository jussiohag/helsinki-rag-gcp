# Plan: helsinki-rag-gcp (2026-09-07)

## Goal
Port the Bedrock RAG demo (Helsinki service points, 21,498 rows) to GCP so the GCP
stack is an artifact: Cloud Run + FastAPI, Vertex AI Search, Gemini, Model Armor, BigQuery,
eval gate in CI, Terraform for europe-north1. Everything runs and is tested offline; the
cloud adapters are real code exercised with fake clients. Deploying is one documented step.

## Non-goals
No voice channel, no agent orchestration, no user accounts. One `/ask` endpoint done well.

## Shared contracts (already in `src/hrag/ports.py`)
`Passage`, `GuardResult`, `Answer`, `Turn`; protocols `Retriever`, `Generator`, `Guard`,
`TurnLog`. `LocalRetriever` exists in `src/hrag/retrieval/local.py`. Do not change these.

## Sprint S1 service (`feat/s1-service`)
- `src/hrag/guard.py`: `HeuristicGuard` (rejects input over 2,000 chars and a short list of
  injection phrases, returns reason) and `ModelArmorGuard` (calls the Model Armor
  `sanitizeUserPrompt` REST endpoint via `httpx`, template name from env
  `HRAG_MODEL_ARMOR_TEMPLATE`, fail closed on error; test with a fake transport).
- `src/hrag/generator.py`: `TemplateGenerator` (deterministic: lists the top 3 passages as
  "name, address, phone" lines, cites their ids, `no_answer=True` when no passages) and
  `GeminiGenerator` (`google-genai` or `vertexai` client, model from env `HRAG_GEMINI_MODEL`
  default `gemini-2.5-flash`, region europe-north1, prompt puts passages in
  `<passage id=...>` blocks and requires `[id]` citations; parse citations, drop unknown ids;
  test with a fake client).
- `src/hrag/retrieval/vertex.py`: `VertexSearchRetriever` using
  `google.cloud.discoveryengine_v1.SearchServiceClient`, serving config from env
  `HRAG_VERTEX_SERVING_CONFIG`, maps results to `Passage`; test with a fake client.
- `src/hrag/turnlog.py`: `JsonlTurnLog` (`turns/turns.jsonl`) and `BigQueryTurnLog`
  (`insert_rows_json` into table from env `HRAG_BQ_TABLE`; fake client test).
- `src/hrag/api.py`: FastAPI app, `POST /ask {question, channel="web", language="fi"}`
  returns `{answer, citations, model, no_answer, latency_ms:{guard,retrieve,generate,log,total}}`;
  `GET /healthz`. Adapter selection from env in `src/hrag/config.py`. Guard rejection returns
  400 with the reason and still logs the turn with `outcome="blocked"`. Tests with `httpx`
  `TestClient` using local adapters: happy path, no-answer, blocked input, latency keys present.

## Sprint S2 eval and ingest (`feat/s2-eval`), parallel
- `eval/golden.jsonl`: 30 cases `{question, expect_any:[row ids], language}` built from real
  rows in `data/helsinki_service_points.csv` (mix fi/en, libraries, daycare, health stations,
  addresses, phone lookups). Pick rows by reading the CSV; ids must exist.
- `eval/run.py`: runs `LocalRetriever` + `TemplateGenerator` (imports from S1 if present,
  otherwise retrieval-only) over the golden set, reports `hit_at_5` (threshold 0.8),
  `citation_ok` (cited ids are a subset of retrieved ids, threshold 1.0), p50/p95 retrieve
  latency, prints a table, exits 1 below thresholds. `make eval` runs it.
- `scripts/ingest_to_jsonl.py`: CSV to Vertex AI Search unstructured-with-metadata JSONL
  (`id`, `structData` with name/address/phone/url, `content.mimeType text/plain`, text
  body), plus `scripts/upload.sh` with the `gcloud storage cp` and
  `gcloud discovery-engine documents import` commands, not executed.
- `tests/test_eval.py`, `tests/test_ingest.py`.

## Sprint S3 infra and CI (`feat/s3-infra`), parallel
- `infra/terraform/`: `versions.tf` (google provider ~> 6), `variables.tf` (project, region
  default `europe-north1`, service name, image, kms key optional), `main.tf`: Artifact
  Registry repo, service account with `roles/discoveryengine.viewer`, `roles/aiplatform.user`,
  `roles/bigquery.dataEditor`, `roles/logging.logWriter` only; Cloud Run v2 service (min 0,
  max 10, concurrency 40, env vars for the adapters, ingress internal-and-load-balancer
  configurable); `google_discovery_engine_data_store` + `search_engine` (location `eu`);
  BigQuery dataset + `turns` table with schema matching `Turn`; `outputs.tf` with the URL.
  Comment where CMEK and VPC Service Controls attach. `terraform fmt` clean.
- `Dockerfile` (python:3.12-slim, uv, non-root, `uvicorn hrag.api:app --port 8080`).
- `deploy.sh`: build with Cloud Build, `terraform apply`, print URL. Not executed.
- `.github/workflows/python-ci.yml`: `make lint test eval`. `.github/workflows/terraform.yml`:
  `hashicorp/setup-terraform`, `make tf-validate`. Both on pull_request and push to main.
- `docs/LATENCY.md`: per-turn budget table (guard 50 ms, retrieve 150, first token 400,
  generate 800, log async) and how `latency_ms` in the response maps to it.
- `docs/COST.md`: monthly estimate at 10k and 100k questions (Cloud Run, Vertex AI Search
  queries, Gemini Flash tokens, BigQuery), with the price assumptions dated.
- Local check: `docker run --rm -v "$PWD/infra/terraform:/w" -w /w hashicorp/terraform:1.9
  fmt -check` then `init -backend=false` and `validate` (network needed for the provider).

## Done when
`make ci` green on main, terraform validate green in CI, all PRs merged, README updated with
the eval table and the deploy command.
