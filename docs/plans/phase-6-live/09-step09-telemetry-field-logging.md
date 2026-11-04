# Phase 6 Step 09 — On-Device Telemetry and Field Logging

## What

Low-overhead, local-only logging that makes every live run measurable after
the fact:

- **System telemetry** every few seconds: battery %, current, battery
  temperature, thermal status and headroom, CPU usage of the app, memory of
  the app (PSS), storage used by the app.
- **Pipeline telemetry**: per stage counts and latencies (sampled), queue
  sizes and ages, drops, mode changes (scheduler, governor, battery),
  model loads / unloads, heavy-model calls.
- **Events**: capture gaps, crashes (stack traces stored locally), questions
  asked (question text only if the user allows; otherwise intent and latency
  only), answers' level and latency.
- **Daily summary** generated on the phone: one small JSON per day.
- **Export**: `task pull-telemetry` over USB; nothing leaves the phone
  otherwise.
- **Laptop report**: `src/benchmarks/field_report.py` turns telemetry into
  daily KPI tables and plots.

## Why

- Field days (Step 13) are only useful if they produce numbers; memory of "it
  felt warm" is not evidence.
- Crash and gap logs make robustness (Step 10) testable.
- Keeping telemetry local respects the offline claim and privacy.

## How to implement

1. `Telemetry` (Kotlin): append-only files rotated daily; sampling interval in
   settings; a ring buffer in memory flushed every minute (crash-safe enough
   for our needs).
2. Measure telemetry's own cost (run with telemetry at low and normal rates).
3. Daily summary at midnight or at the end of a day's run.
4. Laptop report: tables for roadmap §7 KPIs per day, temperature and battery
   plots, mode timelines.

## Open decisions

- **Question text in logs.** Options: (a) never — most private; (b) only with
  an explicit "research mode" switch (draft); (c) always during the field
  study (the user is the only participant).
- **Sampling interval.** Options: (a) 1 s — detailed, more cost; (b) 5 s
  (draft); (c) adaptive (1 s during questions, 10 s otherwise).

## You test this

1. After a 1-hour run, pull telemetry and open the report. Does the
   temperature plot match what you felt?
2. Force a crash in the debug screen; check the crash appears in the log.

## How this number could be lying

- Telemetry adds a little load; its measured cost is subtracted or stated.
- Android PSS memory differs from what the laptop measured (RSS); the report
  says which measure each number uses.

## Verification

- [ ] All listed telemetry recorded on both phones.
- [ ] Telemetry cost measured.
- [ ] Daily summaries generated; laptop report produces KPI tables and plots.
- [ ] No telemetry leaves the phone except by USB pull.

## Files changed

- [NEW] `android/.../live/Telemetry.kt`
- [NEW] `src/benchmarks/field_report.py`
- [MODIFY] `Taskfile.yml` (`pull-telemetry`, `field-report`), `README.md`

## Dependencies

- Step 03.

## Common issues

- Log files growing large on long days; rotate and compress daily.
