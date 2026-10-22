# Phase 6 Step 03 — Live Pipeline Wiring End to End

## What

Connect every on-device component built in Phases 4–5.2 into one live
pipeline, in the frozen configuration:

```
CaptureService frames → Tier 0a / 0b / 0c / 0d → Tier 1 novelty
  → Tier 2 (path C inline, path V queued if the configuration uses it)
  → segmenter → short-term events (provisional) → ledger
audio → VAD → ASR → transcripts → events / ledger
questions → parser → router → answer layer → Ask screen
background: refinement queue, consolidation, conversation processing
```

- Every stage reads from and writes to bounded queues with explicit drop
  policies (Phase 4 Step 09 rules).
- Time-to-queryable is measured: from an event happening to it being
  answerable.
- A "live memory" debug view shows the latest events and ledger changes as
  they are written.

## Why

- Each phase tested its part on replayed data; only the joined pipeline shows
  real interactions: shared CPU, shared memory, shared model instances, queue
  backlogs.
- Time-to-queryable is the user-visible measure of "it remembered": if the
  keys event takes 10 minutes to become answerable, the user will not trust it.

## How to implement

1. A `LivePipeline` coordinator (Kotlin) that owns the queues and stage
   workers (coroutines with limited dispatchers), created by `CaptureService`.
2. Shared model instances (one encoder, one generative model) loaded once and
   shared between stages; loading and unloading policy set by the scheduler
   (Step 04).
3. Queue metrics (size, age of oldest item, drops) exposed to telemetry.
4. Laptop equivalent: the Phase 4 wall-clock replay harness running the same
   joined pipeline on a phone session folder, for debugging with the same
   configuration.
5. Smoke test: 10-minute live run on the Pixel with a state-change script;
   ask "where are my keys?" after each move; measure time-to-queryable.

## Open decisions

- **Model residency.** Options: (a) keep all models loaded — fastest answers,
  most memory; (b) load the generative model only when asked — saves memory,
  adds seconds to first answers; (c) keep loaded on the Pixel, on-demand on the
  Infinix. Measured; feeds Step 04.

## You test this

1. Run the 10-minute live script on the Pixel; after each move, ask where the
   keys are. Note how long it took before the answer was right.
2. Watch the live memory debug view while walking around the room.

## How this number could be lying

- Scripted moves with clear views are the best case for time-to-queryable;
  Step 13's real days show the normal case.

## Verification

- [ ] Joined pipeline runs live for 10 minutes on both phones without crashes.
- [ ] Queue metrics, drops and time-to-queryable logged.
- [ ] Questions answered during capture.
- [ ] Laptop replay of the same joined pipeline works for debugging.

## Files changed

- [NEW] `android/.../live/LivePipeline.kt`, `LiveMemoryDebugScreen.kt`
- [MODIFY] stage classes from Phases 4–5.2 (queue interfaces)
- [NEW] `src/benchmarks/live_replay.py`
- [MODIFY] `README.md`

## Dependencies

- Step 02; parity gates of Phases 4, 4.1, 5, 5.1, 5.2.

## Common issues

- Two stages loading the same model separately doubles memory; check loaded
  model count in the debug view.
