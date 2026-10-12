# Phase 4.1 Step 02 — Final Model Selection with Phone Artifacts and Licences

## What

Freeze the set of models this phase builds on, starting from the Phase 3.1
shortlist (Step 17) and the Probe B and phone spot check results:

- hand landmark / hand detection model,
- image-text embedding model (crop matching, and possibly Tier 1 novelty and
  place recognition — one shared encoder if Phase 4 Step 08 agrees),
- optional small closed-vocabulary detector (for Step 06),
- tracker approach (likely no model: IoU + Kalman written in a few lines).

For each: the exact model file (name, version, hash), the laptop runtime, the
phone runtime, licence status from the ledger, measured laptop and phone
latency (from Phase 3.1 Step 22), and memory footprint.

Output: `docs/results/phase-4.1/model-set.md`, model files placed under
`models/perception/` (git-ignored) with a `task pull-perception-models`
script, and licence ledger rows marked "frozen for Phase 4.1".

## Why

- The same files must run on the laptop and the phones (roadmap §4.1 "same
  artifacts"). Choosing them once, with hashes, prevents silent drift such as
  a newer model version on one side.
- A licence surprise after building is costly; freezing here means every
  later step uses only verified models.
- Memory budget: Gemma 4 E2B already takes about 2.6 GB on disk; perception
  models must fit next to it within the roadmap RAM ceilings (3.5 GB
  flagship, 2.0 GB low-end profile, to be confirmed in Phase 4 Step 02).

## How to implement

1. Start from the Phase 3.1 shortlist and Probe B results; re-check only
   what changed (a newer release, a better phone artifact).
2. For the image-text model, check with Phase 4 Step 08's Pareto results
   whether one encoder can serve novelty, crop matching and places. Record
   the decision and the RAM saved.
3. Download script `task pull-perception-models`: fixed URLs, checksum
   verification, target `models/perception/`. Same files pushed to the
   phones (`task push-perception-models`).
4. Write `model-set.md`: one row per model with file, hash, runtimes,
   licence row link, laptop ms, phone ms (Pixel, Infinix), RAM.
5. Combined memory check on the laptop: load all perception models plus the
   embedder; record peak RSS and compare with the low-end ceiling.

## Open decisions

- **Shared encoder or separate encoders.** Options: (a) one image-text
  encoder for novelty, crop matching and places — least RAM, one runtime,
  may be weaker at one task; (b) separate small encoders tuned to each
  task — best per-task accuracy, more RAM and complexity; (c) shared by
  default, separate only where Step 05 or Step 08 show a large accuracy gap.
- **Detector included at all?** Options: (a) no — crop matching only;
  (b) yes, as a variant tested in Step 06; (c) yes, as the main path for
  medium / large objects with crop matching for small ones. Probe B results
  decide which options are realistic.

## You test this

1. Run `task pull-perception-models` on a clean machine (or after deleting
   the folder). Does it download and verify everything?
2. Read `model-set.md` and confirm each licence row says "verified" with a
   date and link.

## How this number could be lying

- Phone latencies copied from Phase 3.1 Step 22 were single-model, short
  runs. They are labelled "isolated, short" until Step 15 measures the full
  pipeline.
- RSS on the laptop does not equal Android memory accounting (roadmap note
  on PSS); the low-end check is a first warning only.

## Verification

- [ ] Every model has file, hash, runtimes, licence (verified), laptop and
      phone latency, RAM.
- [ ] Download and push tasks verify checksums.
- [ ] Combined laptop memory check recorded against the ceilings.
- [ ] Shared-encoder decision recorded with evidence.

## Files changed

- [NEW] `docs/results/phase-4.1/model-set.md`
- [NEW] `src/perception/models.py` (paths and hashes, loaded through
  `src/config.py` settings)
- [MODIFY] `Taskfile.yml` — `pull-perception-models`,
  `push-perception-models`
- [MODIFY] `docs/results/phase-3.1/licence-ledger.md`
- [MODIFY] `.gitignore` (confirm `/models/` ignored), `README.md`

## Dependencies

- Step 01 (scope). Phase 3.1 Steps 17, 19, 22. Phase 4 Step 08 (shared
  encoder evidence) if available; otherwise decided provisionally and
  revisited.

## Common issues

- Model hosts change URLs; keep the checksum and the original source page in
  `model-set.md`.
- Different preprocessing between the laptop runtime and the phone runtime
  for the same file; write the preprocessing constants once in
  `models.py` and mirror them in Kotlin.
