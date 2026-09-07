# Latency budget

One `/ask` request runs four stages in sequence — guard, retrieve, generate,
log — and the API measures each with a monotonic clock. The response's
`latency_ms` object reports one key per stage plus `total`:

```json
{"guard": 12, "retrieve": 80, "generate": 540, "log": 3, "total": 635}
```

`log` is fired after the answer is already assembled and does not block the
response on the network round trip to BigQuery; a slow or failed log write
adds to `latency_ms.log` for observability but is not on the critical path
that the caller waits on. The other three stages are sequential and do sit
on the critical path, so the perceived latency is `guard + retrieve +
generate`, not `total`.

## Per-turn budget

| Stage             | Budget    | What it covers                                          |
|-------------------|-----------|----------------------------------------------------------|
| guard             | 50 ms     | Model Armor `sanitizeUserPrompt` call (local: heuristic check, near 0 ms) |
| retrieve          | 150 ms    | Vertex AI Search query, top-k passages                  |
| generate: first token | 400 ms | Time to Gemini's first streamed token — a sub-budget inside `generate`, not a separate reported key |
| generate: total   | 800 ms    | Full `generate` stage as reported in `latency_ms.generate`, including the first-token wait above |
| log               | (async)   | BigQuery `insertAll`; not counted toward perceived latency |
| **Perceived total** | **< 1.5 s** | `guard + retrieve + generate`, the time the caller actually waits |

50 + 150 + 800 = 1,000 ms against a 1,500 ms ceiling, leaving roughly 500 ms
of headroom for network variance between Cloud Run and the Vertex/Gemini
APIs before a request breaches the perceived-total budget.

There is no `first_token` key in the API response — streaming
time-to-first-token is a sub-budget used to judge whether `generate` feels
responsive versus merely fast on average, not something the client can read
per request. If per-request first-token timing is ever needed, it would be
a fifth stage split out of `generate` in `Turn.latency_ms` and `ports.py`,
which is out of scope for this sprint.

## When a stage breaches its budget

- **guard > 50 ms**: check Model Armor endpoint latency directly (`gcloud
  logging read` on the guard's Cloud Run request logs); a fail-closed error
  path (network error treated as blocked) can also show up here as a full
  request timeout rather than a slow guard call — check `outcome="blocked"`
  rates in BigQuery alongside the latency number.
- **retrieve > 150 ms**: check Vertex AI Search's own query latency metric
  in Cloud Monitoring before assuming the client call is slow; a cold
  Cloud Run instance adds its own startup cost on top, so also check
  `min_instances` (0 by default — see `infra/terraform/variables.tf`) if
  breaches cluster right after scale-from-zero.
- **generate > 800 ms**: check token count first — `HRAG_GEMINI_MODEL`
  output length is the dominant variable, not network. If prompts are
  consistently long (large passage blocks), reduce `k` in the retrieval
  call before changing the model.
- **log breaching materially (multi-second)**: this does not affect the
  caller, but a sustained backlog means turns are being lost or delayed;
  check BigQuery streaming insert quota and `HRAG_BQ_TABLE` permissions
  first.
- **total > 1.5 s with no single stage over its own budget**: the budgets
  don't leave much slack: check for Cloud Run cold starts (`min_instances`)
  and concurrency saturation (`concurrency = 40` in
  `infra/terraform/variables.tf`) before tuning any one stage.
