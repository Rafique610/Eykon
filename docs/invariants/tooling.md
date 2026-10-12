# Tooling Invariants

Rules for package managers, build tools, and paths.

## Python — `uv`

- Always use `uv` for Python package management. Never call `python` or `pip` directly.
- `uv run <command>` for all execution.
- `uv sync` to install/update dependencies.
- `uv add <package>` to add new dependencies.
- **Windows C++ Packages:** When installing C++ bound packages on Windows (like `llama-cpp-python`), `uv` will hang or fail if Visual Studio Build Tools are missing. *Always* bypass source compilation by using pre-built binary wheels (e.g. configuring `[[tool.uv.index]]` in `pyproject.toml` or using `uv pip install --only-binary`).
- Config: `pyproject.toml` + `uv.lock` (both committed).

## Tests — `pytest`

- pytest is the test framework (dev dependency only, decided 12 October 2026). Tests live in `tests/`, run with `task test`.
- Tests use a temporary database (`tmp_path`). They never touch `data/memories.db`.
- The older one-line health check is `task smoke`.

## Licences

- No AGPL dependencies (for example `ultralytics` / YOLO11). Check a model's and a library's licence before `uv add`, and write it in the card or step.
- Prefer models with a phone-ready export (ONNX / TFLite) so the same file runs on the laptop and on Android.

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
