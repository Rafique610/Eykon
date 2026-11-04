# Phase 6 Step 10 — Robustness: Crash, Kill, Reboot, Storage Full

## What

Deliberately break the live system and check it recovers without losing
memory:

| Test | How | Expected |
|---|---|---|
| App crash during capture | debug "crash now" button | service restarts (where allowed); gap logged; no corrupted database |
| Process killed by Android | `adb shell am kill` / memory pressure app | restart, gap logged, queues resumed or safely dropped |
| Phone reboot during capture | reboot | capture does not silently resume without the user (privacy); memory intact; user notified |
| Storage nearly full | fill storage with a large file | capture pauses with a clear message before the database write fails |
| Database write during kill | kill while a large transaction runs | database consistent (SQLite transactions), no partial events |
| Model file missing / corrupt | rename a model | clear error, fall back to a lower level / mode, no crash loop |
| Long run memory growth | 8-hour run | no steady memory growth (leak check) |
| Clock change / time zone change | change settings | timestamps remain correct (monotonic plus wall time) |

## Why

- A memory assistant that loses a day of memory once is not trusted again.
- Earlier phases tested resumability of individual jobs (for example
  Phase 5.1 Step 11); this step tests the whole live system under failure.
- Several of these (reboot, storage) also have privacy implications (not
  recording silently after a reboot).

## How to implement

1. A test checklist in `docs/results/phase-6/robustness.md` with steps and
   expected results; each test run on both phones.
2. Use SQLite transactions for multi-row writes (already the pattern;
   verify in all live writers).
3. Startup integrity check: SQLite `PRAGMA integrity_check` (or quick check)
   after an unclean shutdown; results logged.
4. Leak check: 8-hour replay or live run with telemetry; memory trend
   plotted.

## Open decisions

- **After reboot.** Options: (a) never auto-resume capture — privacy first
  (draft); (b) auto-resume if the user enabled "always on"; (c) ask with a
  notification after reboot.

## You test this

1. Run three of the tests yourself (crash, kill, storage full) on the Pixel.
   Ask a question about something recorded just before each failure.
2. Reboot during capture and check what the phone does afterwards.

## How this number could be lying

- Forced failures in a quiet moment are easier than failures during heavy
  processing; run the kill test during after-session processing too.

## Verification

- [ ] All tests run on both phones with expected results, or failures fixed /
      documented.
- [ ] Integrity check after unclean shutdowns passes.
- [ ] No memory leak trend over 8 hours.

## Files changed

- [MODIFY] live writers (transactions), startup code (integrity check)
- [NEW] `docs/results/phase-6/robustness.md`
- [MODIFY] `README.md`

## Dependencies

- Steps 03, 09.

## Common issues

- WAL files left after a kill are normal for SQLite; do not delete them
  manually (they hold committed data until checkpoint).
