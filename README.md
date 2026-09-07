# helsinki-rag-gcp

[![CI](https://github.com/jussiohag/helsinki-rag-gcp/actions/workflows/ci.yml/badge.svg)](https://github.com/jussiohag/helsinki-rag-gcp/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Public-service knowledge assistant on GCP. Same question-answering pattern as
the AWS Bedrock version, ported to Cloud Run, Vertex AI Search and Gemini in
europe-north1, with an evaluation gate in CI and a per-stage latency budget.

## Quick Start

```bash
make test      # offline, local retriever over the 21,498-row CSV
make eval      # golden set, hit@5 and citation checks, fails below thresholds
make run       # POST :8080/ask {"question":"Where is the nearest library in Kannelmäki?"}
./deploy.sh    # build on Cloud Build, terraform apply, print the Cloud Run URL
```

## Architecture

```text
 web / phone / chat channel
          |
   Cloud Run (FastAPI)  europe-north1
     guard  -> Model Armor            (local: heuristic)
     retrieve -> Vertex AI Search     (local: keyword over CSV)
     generate -> Gemini 2.5 Flash     (local: template)
     log -> BigQuery turn table       (local: JSONL)
          |
   answer + citations + latency per stage
```

Eval gate, latency budget, cost estimate and Terraform: see
`docs/plans/2026-09-07-helsinki-rag-gcp.md` and `infra/terraform/`.

## Deploy

`./deploy.sh` builds the container on Cloud Build, pushes it to Artifact
Registry, and applies the Terraform module in `infra/terraform/` (see that
directory for the resources it creates). The target project needs these
APIs enabled: `run`, `discoveryengine`, `aiplatform`, `bigquery`,
`artifactregistry`, `cloudbuild`, `modelarmor`.

Per-stage latency budget: [`docs/LATENCY.md`](docs/LATENCY.md).
Monthly cost estimate at 10k/100k questions: [`docs/COST.md`](docs/COST.md).

## License

MIT — see [LICENSE](LICENSE).
