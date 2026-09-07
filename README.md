# helsinki-rag-gcp

[![CI](https://github.com/jussiohag/helsinki-rag-gcp/actions/workflows/ci.yml/badge.svg)](https://github.com/jussiohag/helsinki-rag-gcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Public-service knowledge assistant on GCP. Same question-answering pattern as
the AWS Bedrock version, ported to Cloud Run, Vertex AI Search and Gemini in
europe-north1, with an evaluation gate in CI and a per-stage latency budget.

## Quick Start

```bash
make test      # offline, local retriever over the 21,498-row CSV
make eval      # golden set, hit@5 and citation checks, fails below thresholds
make run       # POST :8080/ask {"question":"Where is the nearest library in Kannelmäki?"}
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

## License

MIT — see [LICENSE](LICENSE).
