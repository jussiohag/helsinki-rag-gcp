.PHONY: setup lint test eval run ingest tf-validate smoke ci

setup:
	command -v uv >/dev/null 2>&1 || python3 -m pip install -q uv
	uv sync --group dev

lint: setup
	uv run ruff check src tests eval scripts

test: setup
	uv run pytest -q

eval: setup
	uv run python -m eval.run

run: setup
	uv run uvicorn hrag.api:app --reload --port 8080

ingest: setup
	uv run python scripts/ingest_to_jsonl.py data/helsinki_service_points.csv build/documents.jsonl

tf-validate:
	cd infra/terraform && terraform fmt -check -recursive && terraform init -backend=false -input=false >/dev/null && terraform validate

smoke: test

ci: lint test eval
