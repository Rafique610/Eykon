# Walkthrough progress

Checklist for the work described in `ANALYSIS.md` (repo root). Read this
file first after a context reset and resume from the first item that is not
**done** or **verified**.

- Status words: **not started** · **in progress** · **done** · **verified**
  (verified = re-checked against the code after it was written).
- Analysed source commit: `89b4da8`. Docs are written on branch `docs` (Phase 0 was committed there by the owner as `52ed52d`).
- Last updated: 22 October 2026, 2:35 PM (UTC+05:00 · 09:35 UTC).
- **Current position: Phase 1 in progress (subagents, five stages at a time).**

## How to resume

1. Read `00-overview.md` §9 (the plan) and §4 (the stages).
2. Formats: `stages/_TEMPLATE.md` (markdown) and `flow/schema.json` (JSON).
3. Scope per stage and the shared node ids: `notes/file-map.md`.
4. Running flags: `notes/flags.md`. Git-log decision notes: `notes/git-decisions.md`.
   Subagent instructions: `notes/agent-brief.md`. Check a stage: `python3 validate_flow.py --stage <id>`.
5. A stage is **done** only when both `stages/<id>.md` and
   `flow/stages/<id>.json` exist and parse.

## Phase 0: Inventory and stage decomposition

| Item | Status | Output |
|---|---|---|
| Repo map: tree, languages, build, dependencies, entry points, config, scripts, tests, datasets, models, skipped list | done | `00-overview.md` §2–3 |
| Git-log notes for the decisions phase | done | `notes/git-decisions.md` |
| Stage decomposition (15 stages), handoffs, draft Mermaid | done | `00-overview.md` §4–6 |
| File-to-stage map (198 source files) and shared node ids | done | `notes/file-map.md` |
| Output formats for Phase 1 | done | `stages/_TEMPLATE.md`, `flow/schema.json` |
| Running flags (29 at the end of Phase 0) | in progress | `notes/flags.md` |
| Owner's go-ahead | done | "continue", 22 October 2026; committed by the owner as `52ed52d` on branch `docs` |

## Phase 1: Per-stage deep dives

| Stage | `stages/<id>.md` | `flow/stages/<id>.json` | Status | Notes |
|---|---|---|---|---|
| s01-intake | — | — | in progress | subagent, batch 1 |
| s02-split | — | — | in progress | subagent, batch 1 |
| s03-keyframes | — | — | in progress | subagent, batch 1 |
| s04-scene | — | — | in progress | subagent, batch 1 |
| s05-small-objects | — | — | in progress | subagent, batch 1 |
| s06-index | — | — | not started | |
| s07-finalise | — | — | not started | |
| s08-video-search | — | — | not started | |
| s09-phone-text-memory | — | — | not started | |
| s10-laptop-text-rag | — | — | not started | |
| s11-laptop-vlm-video | — | — | not started | |
| s12-export-parity | — | — | not started | |
| s13-component-benchmarks | — | — | not started | |
| s14-ego4d-eval | — | — | not started | |
| s15-legacy-benchmarks | — | — | not started | |

## Phase 2: Cross-cutting documents

| Document | Status |
|---|---|
| `02-models-and-algorithms.md` | not started |
| `04-data-and-config.md` | not started |
| `05-design-decisions.md` | not started |
| `06-open-questions.md` | not started |

## Phase 3: Visual flow data

| Item | Status |
|---|---|
| Schema (`flow/schema.json`) | done (drafted in Phase 0, used by Phase 1) |
| All stage JSON files written to the schema | not started |
| `flow/index.json` (stages, stage edges, stage file list, traces) | not started |
| `validate_flow.py` written | done (written early, 22 October, so Phase 1 agents check their own output; tested on planted errors) |
| `validate_flow.py` run, everything it reports fixed | not started |

## Phase 4: Interactive visual

| Item | Status |
|---|---|
| `build_flow.py` + HTML template | not started |
| `flow.html` (self-contained, opens by double-click) | not started |
| Overview level, stage drill-down, breadcrumb | not started |
| Side panel, colours, runtime vs offline styles, [INFERRED]/[UNKNOWN] badges | not started |
| Search, filters, legend | not started |
| Trace-an-input mode | not started |
| Light and dark mode | not started |
| `flow-overview.mmd` | not started |
| `flow-overview.svg` | skipped unless Graphviz or D2 is installed (neither is, 22 October 2026) |

## Final verification

| Item | Status |
|---|---|
| 15+ random claims re-checked against the code, errors fixed | not started |
| `validate_flow.py` passes | not started |
| Summary for the owner | not started |
