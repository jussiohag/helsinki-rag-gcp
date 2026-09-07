# helsinki-rag-gcp, Backlog
<!-- Task stamping: [ ] → [-] 🏗️ YYYY-MM-DD HH:MM → [x] ✅ YYYY-MM-DD HH:MM -->

## Up Next

- [ ] Deploy to a real GCP project via `deploy.sh` and record p95 latency
      from Cloud Run, compared against the budget in `docs/LATENCY.md`.
- [ ] Add an integration test against real Vertex AI Search, gated behind
      an env flag so it is skipped when running offline.
- [ ] Add Swedish and English golden-set cases to the eval gate, alongside
      the current Finnish questions.
- [ ] Add hybrid keyword plus semantic ranking to `LocalRetriever`, so the
      offline twin degrades less on paraphrased questions.
- [ ] Explore an offline mobile app variant, using an on-device model over
      the same Helsinki service-point corpus.
