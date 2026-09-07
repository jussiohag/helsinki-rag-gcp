# Monthly cost estimate

All unit prices below are assumptions as of 2026-09-07, based on Google Cloud's
published on-demand rate cards. Live queries against the pricing pages during
this sprint returned inconsistent numbers from third-party summaries, and the
official Vertex AI pricing page did not return usable content to an automated
fetch. Treat every number here as an estimate to re-check against
`cloud.google.com/*/pricing` before it is used for a budget decision, not as
a quote. Where a price changes, only that one line needs editing. The totals
below are computed from the assumptions stated, not hardcoded separately.

Two volumes: 10,000 questions/month and 100,000 questions/month. One request
= one `/ask` call = one guard check, one search query, one generate call, one
log write.

## Assumptions

| Item | Assumed unit price | Note |
|---|---|---|
| Cloud Run vCPU | $0.000024 / vCPU-second | request-based billing, CPU allocated during request processing only |
| Cloud Run memory | $0.0000025 / GiB-second | |
| Cloud Run requests | $0.40 / 1,000,000 requests | |
| Cloud Run free tier | 2,000,000 requests, 180,000 vCPU-seconds, 360,000 GiB-seconds / month | assumed to apply in europe-north1; verify before relying on it |
| Vertex AI Search query | $4.00 / 1,000 search queries | Enterprise-edition search pricing; excludes any grounding/summarization add-on |
| Gemini 2.5 Flash input | $0.30 / 1,000,000 tokens | text input |
| Gemini 2.5 Flash output | $2.50 / 1,000,000 tokens | text output |
| BigQuery active storage | $0.02 / GB / month | first 90 days of a table's life |
| BigQuery streaming inserts | $0.05 / GB inserted | legacy `insertAll` / `insert_rows_json`, the API `turnlog.py` uses |

Per-question token assumption: 1,500 input tokens, 200 output tokens (passages
plus question in, a short cited answer out).

## Cloud Run

One request is assumed to hold 1 vCPU and 0.5 GiB of memory for 1 second of
billed processing time (roughly the `guard + retrieve + generate` budget in
`docs/LATENCY.md`; `log` runs after the response and is not billed as request
processing time in this estimate).

- 10,000 requests: 10,000 vCPU-seconds, 5,000 GiB-seconds, 10,000 requests,
  all under the free-tier amounts above. Cost: $0.
- 100,000 requests: 100,000 vCPU-seconds, 50,000 GiB-seconds, 100,000
  requests, still under the free-tier amounts above. Cost: $0.

Cloud Run cost only becomes non-zero once monthly traffic pushes past the
free-tier vCPU-second allowance, around 180,000 one-second requests/month at
this sizing.

## Vertex AI Search

- 10,000 questions x $4.00 / 1,000 queries = **$40.00**
- 100,000 questions x $4.00 / 1,000 queries = **$400.00**

## Gemini 2.5 Flash

- 10,000 questions: 15,000,000 input tokens ($4.50) + 2,000,000 output
  tokens ($5.00) = **$9.50**
- 100,000 questions: 150,000,000 input tokens ($45.00) + 20,000,000 output
  tokens ($50.00) = **$95.00**

## BigQuery turn log

Estimated row size from the `turns` table schema
(`infra/terraform/main.tf`): a turn_id, a sha256 question_hash, a handful of
short passage/citation ids, model and outcome strings, and five integers in
`latency_ms`, comes to roughly 0.5 KB/row including BigQuery's per-row
overhead.

- 10,000 rows: ~5 MB total, ~5 MB/month inserted.
  Storage: 0.005 GB x $0.02 ≈ $0.0001. Streaming inserts: 0.005 GB x $0.05 ≈
  $0.0003. Combined: **under $0.01**.
- 100,000 rows: ~49 MB total, ~49 MB/month inserted.
  Storage: 0.049 GB x $0.02 ≈ $0.001. Streaming inserts: 0.049 GB x $0.05 ≈
  $0.002. Combined: **under $0.01**.

BigQuery cost is negligible at both volumes because turn rows carry no
question text, only ids, a hash, and latencies. The table stays small
regardless of question volume.

## Totals

| Monthly questions | Cloud Run | Vertex AI Search | Gemini 2.5 Flash | BigQuery | **Total** |
|---|---|---|---|---|---|
| 10,000 | $0 | $40.00 | $9.50 | <$0.01 | **~$49.50** |
| 100,000 | $0 | $400.00 | $95.00 | <$0.01 | **~$495.00** |

Vertex AI Search is the dominant cost at both volumes, followed by Gemini
generation. Cloud Run and BigQuery do not move the total at this scale.
