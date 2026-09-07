# Contributing to helsinki-rag-gcp

## Environment

```bash
# TODO: add setup instructions
```

## Workflow

1. Branch from `main`: `git checkout -b feat/<short-slug>`
2. Make changes. Write tests first when practical.
3. Run the fast feedback loop:
   ```bash
   make lint
   make test
   ```
4. Commit using conventional format (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`).
5. Push. Pre-push hook runs tests + gitleaks.
6. Open a PR. Fill in the template, describing what changed and why.

## Conventions

- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/)
- **Branches:** `feat/`, `fix/`, `chore/`, `docs/` prefixes
- **PII:** never in tracked files, use `private/` (gitignored)
- **Tests:** ship tests with features when the project has a test suite

## Project Documentation

- `docs/decisions/` (Architecture Decision Records, MADR format)
- `docs/plans/` (implementation plans)
- `docs/postmortems/` (sprint and feature retrospectives)
- Templates: `<pm repo>/templates/`
