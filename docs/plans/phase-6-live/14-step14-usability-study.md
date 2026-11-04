# Phase 6 Step 14 — Usability Study with a Few Users

## What

A short, structured study with 3–5 people other than the developer
(classmates or family, with consent):

1. **Setup** (10 minutes): install or hand over a phone with the app; enrol
   two personal objects; explain pause and delete.
2. **Tasks** (30–40 minutes), each timed and observed:
   - move objects around a room following a short script, then ask "where is
     my X?" at three points,
   - record a 5-minute conversation session with the developer and ask two
     questions about it afterwards,
   - pause recording, mark a place as excluded, delete the last 5 minutes,
   - switch answer style and ask the same question twice.
3. **Questionnaire**: a standard short usability questionnaire (the System
   Usability Scale, 10 statements on a 1–5 scale) plus 4 project questions
   (trust in answers, usefulness of evidence, privacy comfort, battery
   concerns), and open comments.
4. **Analysis**: task success rate, time per task, errors, SUS-style score
   per person and mean, comment themes.

## Why

- The thesis claims a useful assistant; only people other than the developer
  can show whether the features are understandable.
- Privacy controls must be usable to count (a pause button nobody finds does
  not protect anyone).
- A small, well-reported study is honest and expected in an FYP; it is not
  presented as statistically general.

## How to implement

1. Study protocol and consent form adapted from Phase 3.1 Step 03 (no audio of
   participants kept beyond the session unless they agree).
2. Observation sheet per task; the developer does not help unless a
   participant is stuck for more than 2 minutes (recorded as an assist).
3. Results in `docs/results/phase-6/usability.md` with per-participant rows.

## Open decisions

- **Device for participants.** Options: (a) participants use the study
  Pixel — consistent; (b) their own Android phones — realistic, setup varies;
  (c) (a), plus the Infinix for one participant (draft).
- **Number of participants.** Options: (a) 3 — minimum to see patterns;
  (b) 5 (commonly cited as enough to find most usability problems in small
  studies); (c) as many as available within one week.

## You test this

1. Run a pilot session with one friend; fix the protocol.
2. After all sessions, list the top 3 problems participants had and decide
   which to fix before the defense.

## How this number could be lying

- Friends rate the app kindly; observed task success and errors matter more
  than questionnaire scores.
- Lab-style tasks in one room are easier than real use; Step 13 covers real
  use for one person.

## Verification

- [ ] At least 3 participants (target 5) with consent.
- [ ] Task success, times, errors, assists, questionnaire scores recorded.
- [ ] Top problems listed with decisions (fix now / later / not).

## Files changed

- [NEW] `docs/results/phase-6/usability.md`, study protocol and sheets
- [MODIFY] `README.md`

## Dependencies

- Step 13 (system stable after real use).

## Common issues

- Participants' own objects not recognised at all because enrolment photos were
  rushed; observe and record enrolment quality.
