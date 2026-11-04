# Phase 8 Step 12 — Reproducibility Package and Final Repository State

## What

Leave the project in a state where someone else can understand and re-run it:

1. **README** up to date: what Eykon is, architecture, folders, setup (`uv`,
   models download, Android build), and the exact `task` commands that
   reproduce each main result table from the stored results and, where data is
   available, from raw data.
2. **Data statement**: what data exists, what is private and not shared (own
   recordings, consent), what is public (AMI / EPIC subsets with their
   licences), how to obtain public data, the QA set format.
3. **Model statement**: every model file, hash, licence, source (from the
   licence ledger).
4. **Docs tidy-up**: plan docs marked done / cut; domain index
   (`docs/domain/eykon/index.md`) and knowledge map (`docs/docs/index.md`)
   updated with final statuses; outdated docs annotated (not deleted).
5. **Tagged release** of code and app with release notes; results files
   archived.
6. **Retention**: raw recordings handled per consent (deleted or retained per
   university rules) and the deletion recorded.

## Why

- Reproducibility is part of the honesty the project has argued for since the
  first realignment; it also protects the student if results are questioned
  later.
- Stale docs (the domain index still listing Phase 2 as "4/7" was flagged on
  07 October 2026) confuse anyone reading the repository after the defense.

## How to implement

1. Run every README command on a clean checkout (or a fresh environment) and
   fix what fails.
2. Write the data and model statements from the ledgers.
3. Update index docs; annotate old ones.
4. Tag and archive.

## Open decisions

- **Public release of code.** Options: (a) private repository (default); (b)
  public code without data; (c) decided with the supervisor and licence
  constraints of included models.

## You test this

1. On a clean machine (or a fresh folder), follow the README to reproduce one
   main table. Note any missing step.

## How this number could be lying

- Reproducing from stored results only proves the analysis is repeatable, not
  the data collection; the data statement explains the difference.

## Verification

- [ ] README commands reproduce the main tables from stored results.
- [ ] Data and model statements written.
- [ ] Index docs updated; old docs annotated.
- [ ] Release tagged; retention handled per consent.

## Files changed

- [MODIFY] `README.md`, `docs/domain/eykon/index.md`, `docs/docs/index.md`
- [NEW] `docs/results/phase-8/data-statement.md`, `model-statement.md`,
  release notes

## Dependencies

- Step 09 (and all earlier phases).

## Common issues

- Hidden dependencies on files that only exist on the developer's laptop;
  the clean-checkout test finds them.
