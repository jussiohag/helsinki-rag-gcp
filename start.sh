#!/usr/bin/env bash
# Local launcher: uv sync, then uvicorn on :8080 with the local adapters.
set -euo pipefail
cd "$(dirname "$0")"
exec make run
