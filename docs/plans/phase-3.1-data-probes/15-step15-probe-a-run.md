# Phase 3.1 Step 15 — Probe A Run: VLM Extraction on Probe Frames

## What

Run the VLM path on every Probe A frame and store the raw outputs, so they
can be labelled blind in Step 16:

- Gemma 4 E2B (LiteRT-LM, the model already used in Phases 2 and 3) with
  (1) the Phase 3 free caption prompt and (2) the Step 02 slot prompt,
- optionally Moondream2 and PaliGemma through the existing Phase 3 llama.cpp
  path (`src/benchmarks/_captioners.py`), if they are still installed —
  same prompts adapted to their format,
- every output converted to a slot record (the free caption is parsed into
  the `objects` list by simple matching against the session vocabulary, and
  also kept verbatim in `caption`),
- cost per frame measured under the Mobile Emulation Profile rules that are
  already possible on the laptop (CPU only, thread count fixed, peak memory
  recorded).

Output: `data/probes/a/outputs.jsonl` (one line per frame × model × prompt)
and `data/probes/a/run_meta.json` (model files and hashes, prompts, settings,
machine, start and end time).

## Why

- Step 16 needs outputs to label. Separating the run from the labelling
  keeps the labeller blind and lets the run be repeated exactly.
- Running both the free caption prompt and the slot prompt on the same
  frames measures whether asking for structured output changes invention
  and miss rates (the risk noted in Step 02).
- Phase 3 already compared models on 3 short stock clips. This is the first
  comparison on our own egocentric frames, with small objects and dim light
  where errors are expected.

## How to implement

1. **Runner** `src/probes/probe_a.py`: reads `frames.json`, loops over
   frames × configurations, calls the existing captioning functions (reuse
   `src/vision/captioner.py` and `src/benchmarks/_captioners.py`; do not
   write new model wrappers), writes one JSON line per call immediately
   (so a crash loses nothing), resumes from where it stopped.
2. **Emulation rules available now**: force CPU (no GPU layers), fix thread
   count (4), record peak resident memory per call with `psutil` (already a
   dependency). Full wall-clock replay and RAM caps belong to Phase 4 Step 02
   and are not needed for single-frame probes.
3. **Slot conversion**: slot prompt output → JSON parse → `validate_slot`.
   Free caption → vocabulary matching (lower-case, singular, synonyms) →
   `objects`. Unmatched nouns are kept in a separate `unmatched_nouns` list
   for the labeller to see (they may be correct objects outside the
   vocabulary, or inventions).
4. **Failures are data**: timeouts, parse failures and empty outputs are
   recorded with the reason and counted in Step 16, never dropped.
5. **Run order**: randomise the order of configurations per frame (seeded)
   so that thermal or memory effects over time do not always hit the same
   model.
6. **Determinism**: temperature 0 (or the most deterministic setting the
   runtime allows) and fixed prompt text; settings in `run_meta.json`.
7. **Size of the run**: at least 120 frames × at least 2 configurations.
   At the Phase 3 laptop speed (about 13 s per frame in the soak test), 240
   calls take roughly an hour; more models scale linearly. Measured time is
   written into `run_meta.json`.

## Open decisions

- **Which extra VLMs to include.** Options: (a) Gemma 4 E2B only — fastest,
  answers the main question about the model we actually ship; (b) plus
  Moondream2 and PaliGemma from Phase 3 — reuses existing setup, gives a
  comparison; (c) plus a smaller VLM candidate (SmolVLM family, roadmap §8
  open decision on the primary VLM) — informs the "small model for provisional
  captions" question, but needs a new download, licence check and a phone
  artifact check first.
- **Frame resolution given to the VLM.** Options: (a) the 640×480 the phone
  pipeline will deliver (Step 06) — honest to the product; (b) the full
  1080p frame — shows the best case; (c) both for a 30-frame subset to
  measure the effect of resolution. The draft uses (a) for the main run.

## You test this

1. Before the full run, run `task probe-a -- --limit 5` and look at the 10
   outputs (5 frames × 2 prompts). Do they look like normal model output, or
   is something broken (empty, truncated, wrong frame)?
2. During the full run, check `outputs.jsonl` grows and the laptop is not
   swapping memory.
3. Do **not** read the outputs closely after the smoke test; you will label
   them blind in Step 16.

## How this number could be lying

- Laptop latency is not phone latency. Step 22 measures the phone; here
  latency is labelled "laptop, emulation profile".
- Vocabulary matching on free captions can create false "inventions" (the
  caption says "keyring", the vocabulary says "keys") or hide them. The
  synonym list is fixed before the run; the labeller sees the original
  caption, not only the matched list.
- Temperature 0 makes outputs repeatable but may not be the setting used in
  the product. The product setting is recorded and, if different, a 30-frame
  rerun at the product setting is added.

## Verification

- [ ] Pre-registration committed before this run (Step 13).
- [ ] `outputs.jsonl` has one line per frame × configuration, including
      failures with reasons.
- [ ] `run_meta.json` has model file hashes, prompts, settings, machine,
      timings.
- [ ] Slot prompt parse failure rate reported.
- [ ] The run is resumable (tested by stopping and restarting).
- [ ] `probe_a.py` under 300 lines and reuses existing captioning code.

## Files changed

- [NEW] `src/probes/probe_a.py`
- [NEW] `data/probes/a/outputs.jsonl`, `run_meta.json` (git-ignored)
- [MODIFY] `Taskfile.yml` — `probe-a`
- [MODIFY] `README.md`

## Dependencies

- Step 02 (slot schema and slot prompt), Step 13 (pre-registration),
  Step 14 (sampled frames).

## Common issues

- LiteRT-LM image input format differs from llama.cpp's; reuse the
  conversion already written for Phase 3 Step 04 / Step 08.
- Long runs on a laptop on battery get throttled; plug in and record it.
- Gemma sometimes describes the photo style ("a blurry image of…") instead of
  objects; that is not an invention, the labelling criteria say how to treat
  it.
