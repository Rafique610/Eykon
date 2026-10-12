# Phase 6 Step 13 — Multi-Day Field Study with Full-Day Runs

## What

The user lives with the system for at least 5 days (planning: field-study
plan from Step 01), wearing the phone on the mount during set hours, with the
frozen configuration:

- **Daily routine**: start memory in the morning, normal life, at least 10
  real questions per day asked when actually needed (not scripted), a short
  evening check where the user answers 10 prepared questions about the day
  (written by the user during the day in a notebook, without looking at the
  app) — giving real-world QA with ground truth from the notebook.
- **Daily KPIs** from telemetry: hours recorded, gaps, battery used per hour,
  temperature, mode time shares, heavy calls per hour, storage growth per
  hour, answer latency P50 / P90, questions answered correct / partly / wrong
  (user-judged), refusals.
- **At least one full-day run** per phone (Pixel primary for most days; the
  Infinix for at least one full day).
- **Multi-day data** for Phase 5 Step 06 (semantic memory / routines) and
  Phase 5 Step 10 (lifecycle over days).
- **Diary**: a short daily note of annoyances, surprises and privacy moments
  ("it recorded my friend before I paused").

## Why

- Roadmap Phase 6 core question: "does it survive a real day on a real
  phone?". Only real days answer it.
- Real questions asked when needed are the most honest measure of usefulness;
  scripted questions overestimate it.
- Several earlier steps (semantic memory, lifecycle over days, exclusion
  places) need real multi-day data.

## How to implement

1. Daily checklist from Step 01; telemetry pulled each evening
   (`task pull-telemetry`), daily report generated.
2. Real questions logged with time and the user's judgement (research mode).
3. Evening check questions and notebook answers typed into a QA file
   (`data/field/qa_fieldday_<n>.json`), scored automatically / by the user.
4. After 5 days: run Phase 5 Step 06 routine discovery and Step 10 lifecycle
   pass on the real data; record results there.
5. Summary report: per-day tables, trends over days (storage, latency growth),
   worst day, diary themes.

## Open decisions

- **Hours per day.** Options: (a) 8 hours — full working day, heavy;
  (b) 4 hours at set times — easier to keep up for 5 days; (c) 8 hours on
  2 days, 4 hours on 3 days (draft).
- **Who writes evening questions.** Options: (a) the user during the day
  (draft) — natural; (b) a friend who was there — independent, rarely
  available; (c) generated from telemetry — biased toward what the system
  saw.

## You test this

This step is you using the app for real. Each evening, read the daily report
and add one paragraph to the diary: would you keep using it tomorrow, and why?

## How this number could be lying

- One user (the developer) is not a user study; Step 14 adds other people
  briefly.
- The developer avoids situations they know break the system; the diary
  records any avoided situations honestly.
- Questions written in a notebook during the day are about things the user
  noticed; things they did not notice (the common case for lost items) are
  under-represented.

## Verification

- [ ] At least 5 field days with daily KPI reports; at least one full day per
      phone.
- [ ] Real questions and evening-check questions scored.
- [ ] Phase 5 Steps 06 and 10 run on the real data.
- [ ] Summary report with trends, worst day, diary themes.

## Files changed

- [NEW] `data/field/` (git-ignored), `docs/results/phase-6/field-study.md`
- [MODIFY] `README.md`

## Dependencies

- Steps 11, 12 (live system proven on short runs first).

## Common issues

- Forgetting to start memory in the morning; a daily reminder notification
  (local) helps; missed hours are logged, not hidden.
