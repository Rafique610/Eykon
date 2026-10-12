# Phase 5.1 Step 11 — After-Session Processing While Charging

## What

Run the heavy conversation processing (ASR, diarization, alignment, topics,
summaries, action items) on the phone **after** the session, preferably while
charging, with clear progress and safe interruption:

1. a chain of Android WorkManager jobs per session:
   transcribe → diarize → align → topics → summaries → action items,
   each job idempotent and resumable,
2. constraints: by default "charging and battery above X %" for the
   generative parts; ASR may run immediately if the user asks
   ("process now"),
3. progress shown in the session list ("transcribing 40 %"), with an
   estimated time based on measured speed on that phone,
4. a laptop simulation of the same chain (`src/conversations/scheduler.py`)
   for testing and for pre-recorded sessions,
5. measurements: processing time per 30-minute session per stage, battery
   used, peak temperature and thermal status, on both phones.

## Why

- Roadmap v2: "run after the session or while charging". This is part of the
  panel's third complex-computing component (performance and thermal
  management across audio and text with a local model).
- Running a 2B model for summaries while the phone is in a pocket during the
  day risks heat and battery drain (the Infinix already averaged 4.68 W in a
  query-only run). Charging time is free compute.
- Resumable jobs make long processing robust to the phone being unplugged or
  the app being killed.

## How to implement

1. Android: `ConversationPipelineWorker` per stage with WorkManager chaining
   and constraints from settings; each stage writes its outputs and a
   completion marker before the next starts.
2. Stage outputs stored in the session folder and database (as on the
   laptop), so laptop and phone outputs can be compared for the parity gate.
3. Thermal guard: if thermal status reaches a set level, pause the stage
   (WorkManager retry with backoff) and record the pause.
4. "Process now" override for the user, which still respects the thermal
   guard.
5. Laptop scheduler for the same chain with the same stage order and resume
   behaviour.
6. Telemetry per stage: start, end, battery %, battery temperature, thermal
   status, peak memory; exported for Step 18.

## Open decisions

- **Default constraint.** Options: (a) everything only while charging —
  safest, results hours later; (b) ASR immediately, generative parts while
  charging (draft) — transcript soon, summaries later; (c) everything
  immediately — fastest, hottest.
- **Low-end mode for the Infinix.** Options: (a) same pipeline, just slower;
  (b) smaller ASR and extractive summaries only; (c) user setting. Decided
  with Step 18 numbers.

## You test this

1. Record a 30-minute session on the Pixel, plug in the charger, and watch the
   progress until summaries appear. How long did it take?
2. Unplug halfway; plug back in. Does it continue where it stopped?
3. Repeat on the Infinix; feel how warm it gets.

## How this number could be lying

- Processing times on a cool phone on a desk are better than in a warm room or
  a phone case; record room temperature and starting battery temperature.
- Charging changes thermal behaviour (charging adds heat); report "on
  charger" and "on battery" runs separately.

## Verification

- [ ] Chain runs to completion for a 30-minute session on both phones.
- [ ] Interruption and resume tested at every stage.
- [ ] Thermal guard pauses and resumes correctly (forced by a low test
      threshold).
- [ ] Per-stage time, battery and thermal telemetry exported.

## Files changed

- [NEW] `android/.../conversations/ConversationPipelineWorker.kt` and stage
  workers
- [NEW] `src/conversations/scheduler.py`
- [MODIFY] `src/config.py`, `Taskfile.yml` (`session-process`), `README.md`

## Dependencies

- Steps 03–10 (stages), Step 02 (sessions).

## Common issues

- WorkManager may delay jobs for a long time on some phones (battery
  optimisation); record actual start delays.
- Loading the generative model for each topic separately wastes time; load
  once per stage and keep it while that stage runs.
