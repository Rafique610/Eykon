# Phase 4.1 Step 11 — Integration as Tier 2 Path C in the Phase 4 Cascade

## What

Plug the cheap perception pipeline into the Phase 4 cascade as the Tier 2
"path C" implementation (Phase 4 Step 09 two-path interface), and run it
under **wall-clock replay** with the Mobile Emulation Profile:

- `MEMORY_EXTRACTION_PATH=cheap` and `both` work end to end: frames → gates →
  (hand-activity gate, if kept) → path C → slot records → segmenter → memory,
- in `both` mode, path C runs inline and path V (VLM) runs behind the
  bounded queue as refinement (the Phase 4 Step 09 option (d)),
- measure: per-frame cost of path C, backlog and dropped frames, heavy-model
  calls per hour in each mode, time from event to queryable record.

## Why

- Path C was evaluated offline so far. Live use means frames arrive at real
  speed; if path C cannot keep up, its accuracy does not matter.
- The `both` mode is the likely real design (cheap now, VLM refinement when
  free); its cost and benefit must be measured, not assumed.
- Phase 4's ablation (B6-C) needs this integration to run.

## How to implement

1. Implement `extract_cheap(frame, context) -> list[SlotRecord]` behind the
   Phase 4 Tier 2 interface, calling `src/perception/runner.py` in streaming
   mode (state kept between frames).
2. Wire settings: `MEMORY_EXTRACTION_PATH`, path C rate limits.
3. In `both` mode, path V refinement records reference the path C record they
   refine (`refines: record_id`), so the ledger can see both.
4. Run wall-clock replay on 3 tuning sessions (desk, kitchen, walking) in
   modes `vlm`, `cheap`, `both`; collect run folders.
5. Report: per-stage latency P50 / P90, dropped frames, backlog max, calls
   per hour by model type, time-to-queryable P50 / P90.

## Open decisions

- **Path C rate under load.** Options: (a) run on every cascade-passed frame
  and drop frames when busy — simple, may miss quick events; (b) priority to
  frames flagged by the hand gate — focuses compute; (c) adaptive frame
  skipping by measured latency. Draft: (b), measured against (a).

## You test this

1. Run `task replay -- <kitchen session> --path both` and watch the live
   debug view: are events appearing within a few seconds of the action?
2. Compare the run summaries for `vlm`, `cheap` and `both`. Which would you
   choose for your phone, and why?

## How this number could be lying

- Laptop wall-clock replay with 4 threads is still faster than a phone;
  Step 15 measures the phones.
- Three sessions are a smoke test for integration; accuracy claims come from
  Step 12.

## Verification

- [ ] All three modes run end to end under wall-clock replay.
- [ ] Refinement links (`refines`) present in `both` mode.
- [ ] Cost, backlog, calls per hour and time-to-queryable reported per mode.
- [ ] Phase 4 Step 11 can run B6-C with this integration.

## Files changed

- [MODIFY] `src/vision/extract.py` (Tier 2 interface, path C hook)
- [MODIFY] `src/perception/runner.py` (streaming mode), `src/config.py`
- [NEW] `docs/results/phase-4.1/step11-integration.md`
- [MODIFY] `Taskfile.yml`, `README.md`

## Dependencies

- Step 10; Phase 4 Step 09 (Tier 2 interface) and Phase 4 Step 02 (replay).

## Common issues

- Shared encoder used by Tier 1 and path C at the same time: load once and
  share the instance, or memory doubles.
