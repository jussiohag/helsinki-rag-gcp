# helsinki-rag-gcp, Roadmap
<!-- Task stamping: [ ] → [-] 🏗️ YYYY-MM-DD HH:MM → [x] ✅ YYYY-MM-DD HH:MM -->

## Vision

A public-service knowledge assistant that answers questions about Helsinki
service points (libraries, daycares, health stations) with citations, and
runs the same way locally and on GCP through a small adapter layer.

## Phases

- [x] Phase 1: local twins. FastAPI request path, offline retriever,
      generator and guard, golden-set eval gate, web UI, architecture docs.
      ✅ 2026-09-07
- [ ] Phase 2: cloud deploy. Wire the Vertex AI Search, Gemini and Model
      Armor adapters to a real GCP project, deploy with Terraform, and
      confirm the latency budget holds under real network conditions.
- [ ] Phase 3: offline app. Package the local twins into a mobile app that
      answers the same questions with an on-device model, no network
      required.
