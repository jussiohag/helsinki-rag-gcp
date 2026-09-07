.PHONY: lint test build ci smoke

lint:
	@echo "TODO: configure linter (eslint, ruff, clippy, golangci-lint)"

test:
	@echo "TODO: configure test runner (jest, pytest, cargo test, go test)"

build:
	@echo "TODO: configure build (npm run build, cargo build, go build)"

smoke:
	@echo "TODO: configure smoke tests"

ci: lint test build
