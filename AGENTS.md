# helsinki-rag-gcp

## Project
TODO: add project description

## Commands
- Build: N/A
- Test: N/A
- Lint: N/A

## Creating repositories
- Use the `initialize-project` skill when creating or bootstrapping a repository.
- Games and game prototypes use `~/coding/newgameproject/bin/newgameproject.sh` with the appropriate stack flag.
- All non-game repositories use `~/coding/pm/hooks/newproject.sh`.
- Do not replace the maintained initializers with manual `git init`/template copying because an interactive shell alias is unavailable.

## Conventions
- Task stamping: [ ] → [-] 🏗️ YYYY-MM-DD HH:MM → [x] ✅ YYYY-MM-DD HH:MM
- Branch workflow: feature branches, no direct commits to main
- PII: never in tracked files, use private/ (gitignored)
- Commits: conventional format (feat:, fix:, docs:, chore:), no Co-Authored-By
- Coverage targets: 80% Rust domain, 60% GDScript, 80% TypeScript libraries

### Code as a document

Code is read far more than written. The reader wants the final design, not
the edit log.

- Comments explain WHY, assumptions, and non-obvious context. Never what the
  next line obviously does, and never what changed ("now uses X", "changed
  from Y") — that belongs in the commit message.
- Distribute context: short inline comments at logical sections of the body,
  not one giant block above the function. A doc comment longer than the
  function is a smell.
- Respect the eye: a function fits on one screen (~40 lines soft cap). If you
  scroll to understand one function, extract or restructure.
- Narrative order: entry point first, helpers in the order they are called.
  The file reads top to bottom like a story.
- Match the surrounding code's comment density and idiom when editing.

### TypeScript
- Strict mode always (`"strict": true`)
- Biome for linting/formatting (not ESLint/Prettier)
- Naming: camelCase functions/vars, PascalCase types, UPPER_SNAKE_CASE constants, snake_case files
- Errors: Result<T, E> pattern for library APIs (errors as values, not exceptions)
- Exports: explicit named exports, no `export *`
- Testing: Vitest, co-located (`foo.test.ts` next to `foo.ts`)
- ESM-first, `"type": "module"`

### Rust
- Module style: `mod.rs`, `pub use` re-exports
- Errors: `thiserror` for domain, `anyhow` only at app boundary
- Lints: `clippy::correctness = "deny"`, `clippy::all = "warn"`
- Domain purity: no framework deps (Bevy/Godot) in domain layer
- Testing: inline `#[cfg(test)]` for unit, `tests/` for integration

### GDScript
- Official style guide (docs.godotengine.org)
- Type hints always (`var health: int = 100`, `func foo() -> void:`)
- Signals: past tense (`health_changed`, `player_died`)
- Scene refs: `%UniqueNames` not `$Full/Path`
- Script order: signals → enums → constants → @export → @onready → vars → _ready → _process → public → private

## Hooks
- Pre-commit: PII + secrets + QA (auto-detect)
- Pre-push: build + tests + gitleaks
- Config: .hooks-config, .hooks-allowlist

## Documentation
- `docs/decisions/` — ADRs (MADR format, template: ~/Desktop/coding/pm/templates/adr-template.md)
- `docs/plans/` — implementation plans (save here, not project root)
- `docs/postmortems/` — sprint and feature retrospectives

## System reference
- Full PM system docs: ~/Desktop/coding/pm/docs/PM-SYSTEM.md
- Decisions: ~/Desktop/coding/pm/decisions/
- Templates: ~/Desktop/coding/pm/templates/
