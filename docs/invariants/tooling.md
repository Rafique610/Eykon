# Tooling Invariants

Rules for package managers, build tools, and paths.

## Python — `uv`

- Always use `uv` for Python package management. Never call `python` or `pip` directly.
- `uv run <command>` for all execution.
- `uv sync` to install/update dependencies.
- `uv add <package>` to add new dependencies.
- Config: `pyproject.toml` + `uv.lock` (both committed).

## Task Runner — `Taskfile.yml`

- Every runnable command gets a Taskfile entry.
- Users should never memorize raw commands — `task <name>` is the interface.
- Existing tasks: `run`, `install`, `pull-model`, `check-config`, `benchmark`, `test`, `test-e2e`, `test-android`, `build-android`.
- New tasks for Phase 3: `pull-vlm`, `check-vlm`, `benchmark-vision`, `soak-test`, `experiment`, `test-vision-integration`.

## Paths

- Project root: `c:\Users\rafique_\Desktop\New folder\FYP_Demo`
- Source code: `src/`
- Models: `models/` (git-ignored, downloaded via `task pull-model`)
- Data: `data/` (git-ignored, contains SQLite DBs)
- Plans: `docs/plans/`
- Memory log: `.memory/<date>/tasks.md` (git-ignored)

## Docker (When Used)

- Two-stage Dockerfiles for small images.
- Credentials via `${VAR}` in compose, never inline.
- DNS failures: retry at least 3 times before giving up.

## Android (Phase 2)

- Kotlin + Jetpack Compose.
- LiteRT-LM for on-device inference.
- Build via `task build-android`.
