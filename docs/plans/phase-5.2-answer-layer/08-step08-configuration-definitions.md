# Phase 5.2 Step 08 — Configuration Definitions L0–L3 and the Perception Switch

## What

Make each configuration a **single, named setting** that switches everything
it implies, so a configuration cannot be half-applied:

| Setting | `MEMORY_CONFIG=L0` | `L1` | `L2` | `L3` |
|---|---|---|---|---|
| Extraction path (Phase 4 Step 09) | `cheap` (path C) or `none` + image-text keyframe retrieval if Phase 4.1 is cut | as L0 | as L0 | `vlm` (path V) |
| Speech | VAD + ASR | same | same | same |
| OCR | on | on | on | on (or VLM reads text, if Phase 5.1 chose that) |
| Time parser / router | rules | rules | rules | rules (LLM fallback allowed only if Phase 5 measured it helps) |
| Summaries (Phase 5.1) | extractive | extractive | generative | generative |
| Action items | rules | rules | generative + rules | generative + rules |
| Answer levels allowed | T, Q | T, Q, X | T, Q, G | T, Q, G |
| Default level (`auto`) | T / Q by intent | X for factual text, else T / Q | G | G |

Plus:

- **Memory build per configuration**: perception-dependent memory (events,
  ledger) must be built from the same recordings with each perception path,
  stored in separate databases (`data/configs/L0/memories.db`, …), so answers
  in L0 never use VLM-derived memory.
- **Config manifest**: each configuration writes `config_manifest.json`
  (all settings, model hashes, prompt ids, database hash) — the only valid
  description of what ran.

## Why

- The comparison is only fair if each configuration is complete and
  isolated. A common mistake is answering L0 questions from a database that
  was built with VLM captions; separate databases make that impossible.
- One setting is easy to explain to the panel ("L0 = no generative model
  anywhere") and easy to verify from the manifest.
- The fallback for L0 objects when Phase 4.1 is cut is written down now, so
  the L0 result is not silently weakened or strengthened later.

## How to implement

1. `src/answers/configs.py`: a dictionary of configuration definitions and
   `apply(config_id)` that sets all dependent settings (Pydantic settings
   object, no environment variable reads).
2. `task build-config-db -- L0` builds the memory database for a
   configuration from the Phase 3.1 recordings using the frozen Phase 4 / 4.1
   / 5 / 5.1 pipelines; one per configuration (L1 shares L0's database; L2
   shares L0's perception but has generative summaries — so it gets its own
   database or a separate summaries table, decided below).
3. Guard: at answer time, the configuration id in the request must match the
   database's manifest; mismatch is an error.
4. "No generative model" check for L0 / L1: the call counter from Step 01 must
   show zero generative calls over a whole run; the run fails otherwise.

## Open decisions

- **L2 database.** Options: (a) separate database with generative summaries
  and action items — clean; (b) shared with L0, plus a `level` column on
  summaries and action items (already in the Phase 5 schema) — less disk,
  needs filtering by level; (c) (b) with a guard test. Draft: (c).
- **L0 objects when Phase 4.1 is cut.** Options: (a) image-text retrieval of
  keyframes for "where is X" (show the best-matching frame and its time) —
  weak but honest; (b) report object categories as "not supported in L0";
  (c) (a) plus the Probe B prototype records. Decided from the Gate 1 outcome.

## You test this

1. Run `task build-config-db -- L0` and `-- L3` on one session. Open both
   databases and compare one event's records: L0 has no VLM caption, L3 does.
2. Ask the same question with `MEMORY_CONFIG=L0` and `L3` and read the
   manifests printed with the answers.

## How this number could be lying

- Building databases at different times with slightly different code would
  mix code changes into the comparison; all databases are built from the
  same commit, recorded in the manifest.

## Verification

- [ ] Four configurations defined; `apply()` sets every dependent setting.
- [ ] Databases built per configuration with manifests and hashes.
- [ ] Guard rejects mismatched configuration and database.
- [ ] Zero generative calls in a full L0 and L1 run (counter check).

## Files changed

- [NEW] `src/answers/configs.py`
- [MODIFY] `src/config.py`, `Taskfile.yml` (`build-config-db`)
- [NEW] `docs/results/phase-5.2/configs.md`
- [MODIFY] `README.md`

## Dependencies

- Steps 03–07; Phase 4 Step 09 (two-path interface); Phase 4.1 Step 11 (path
  C) if in scope; Phase 5.1 Steps 09–10 (summary / action levels).

## Common issues

- Building L3 databases is slow (VLM over all keyframes); reuse the frozen
  Phase 4 path V outputs where they already exist instead of recomputing.
