# Phase 6 Step 01 — Kickoff: Gate 3 Configuration, Live Targets, Field-Study Plan

## What

1. **Freeze the live configuration** chosen at Gate 3 (Phase 5.2 Step 15):
   perception path, answer default level, models and hashes, all thresholds
   from the frozen configs of Phases 4, 4.1, 5, 5.1, 5.2. Written to
   `docs/results/phase-6/live-config.json` with a hash.
2. **Live targets**: copy the roadmap §7 KPIs that apply live (thermal events,
   battery per 30 minutes, storage per hour, heavy calls per hour, answer
   latency, network calls) and add the Phase 6 specific ones (recording gaps,
   recovery time, dropped frames under load); the user confirms target and
   minimum values.
3. **Field-study plan**: dates, places, mount, which phone on which day,
   daily routine ("wear it from 9 am to 6 pm, ask at least 10 questions"),
   consent for any meetings, what to do if something breaks.
4. **Measurement protocol** shared by all live runs: phone state at start
   (battery %, temperature, brightness, background apps closed, airplane
   mode), how to carry it, how results are pulled.

## Why

- Live runs are expensive in time; changing the configuration halfway makes
  results incomparable. Freezing it first protects them.
- Targets written before the runs keep the evaluation honest (same principle
  as every earlier phase).
- A field study without a plan produces days of unusable data (phone left in a
  bag, forgotten mount, no questions asked).

## How to implement

1. Collect frozen configs by script into `live-config.json`; verify all model
   files on both phones by hash.
2. Targets table in `docs/results/phase-6/kickoff.md`.
3. Field-study calendar and daily checklist in the same document.
4. Measurement protocol as a one-page checklist.

## Open decisions

- **Field-study length.** Options: (a) 5 days (minimum, roadmap Phase 5
  Step 06 needs "at least 5 days"); (b) 7 days — includes a weekend routine;
  (c) 5 days on the Pixel plus 2 on the Infinix. Time decides.
- **Mount during field days.** Options: (a) chest clip all day; (b) chest clip
  for set hours, phone in hand otherwise; (c) alternate days between chest and
  head mount (feeds Phase 7). Draft: (a).

## You test this

1. Confirm the targets table as the user.
2. Do a 1-hour "dress rehearsal" of a field day with the checklist; note
   anything awkward.

## How this number could be lying

- Targets copied from the roadmap were written before any phone data;
  Step 15 reports results against them and explains any target that turned out
  unrealistic, without silently changing it.

## Verification

- [ ] Live configuration frozen with hash; model hashes verified on both
      phones.
- [ ] Targets confirmed by the user.
- [ ] Field-study plan and measurement protocol written.
- [ ] Dress rehearsal done.

## Files changed

- [NEW] `docs/results/phase-6/live-config.json`, `docs/results/phase-6/kickoff.md`
- [MODIFY] `README.md`

## Dependencies

- Phase 5.2 Step 15 (Gate 3).

## Common issues

- A late bug fix after freezing: allowed only with a new config hash and a
  note listing which runs used which hash.
