# Contributing to helsinki-rag-gcp

## Environment

```bash
make setup    # uv sync, installs uv if missing
make test     # pytest
make lint     # ruff
make eval     # golden set, exits 1 below threshold
make run      # uvicorn on :8080, browser UI at /
```

No cloud account is needed. Every cloud adapter has a local twin, selected by
environment variables (`HRAG_RETRIEVER`, `HRAG_GENERATOR`, `HRAG_GUARD`,
`HRAG_TURNLOG`); the default is always local.

## Workflow

1. Branch from `main`: `git checkout -b feat/<short-slug>`
2. Make changes. Write tests first when practical.
3. Run `make lint` and `make test`.
4. Commit using conventional format (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`).
5. Push and open a PR. Describe what changed and why.

## Layout

- `src/hrag/ports.py` dataclasses and protocols shared by all modules
- `src/hrag/retrieval/` `local.py` keyword retriever, `vertex.py` Vertex AI Search adapter
- `src/hrag/generator.py`, `guard.py`, `turnlog.py`, `api.py` the request path
- `eval/` golden set and runner, `scripts/` ingestion, `infra/terraform/` GCP resources
- `docs/ARCHITECTURE.md` and `docs/plans/` design and implementation plan

## Conventions

- Type hints everywhere. Cloud clients are created lazily inside the adapter
  and only when the selecting environment variable is set.
- Cloud adapters are unit-tested with a fake client; no test needs credentials
  or network.
- Stage latencies (guard, retrieve, generate, log) are measured per request and
  returned in the response.
- Turn logs never contain the question text, only its hash, ids, model and
  latencies.
- Every module gets `tests/test_<module>.py`. Tests first for behaviour changes.
- Commits: [Conventional Commits](https://www.conventionalcommits.org/), no
  tool attribution lines.
- Branches: `feat/`, `fix/`, `chore/`, `docs/` prefixes.
- No personal data in tracked files.

## Project documentation

- `docs/decisions/` Architecture Decision Records, MADR format
- `docs/plans/` implementation plans
- `docs/postmortems/` retrospectives
