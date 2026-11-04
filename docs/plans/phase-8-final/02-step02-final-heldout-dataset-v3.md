# Phase 8 Step 02 — Final Held-Out Dataset v3: Recordings and Questions

## What

Record new data after the freeze, following the Phase 3.1 protocol and
consent rules:

- **Objects / daily life**: at least 1 hour in places never used before
  (roadmap v2 §5 item 9: "new places"), with state-change scripts and
  unscripted parts, annotated with the Phase 3.1 tools.
- **Meetings**: at least 2 new meetings (new agendas; at least one with a
  participant who was not in earlier meetings, if possible), annotated.
- **Lecture** (if classroom is in scope): 1 new session.
- **Questions**: at least 30 per category across the new data where the data
  allows (otherwise the shortfall stated), written **before** running the
  system, with at least a third written by someone other than the developer.
- **Phone capture**: recorded with the product capture path (Phase 6 capture
  service in recording mode) so the input is exactly what the product sees.

## Why

- Every earlier held-out set was opened at some point during the project; v3
  is the only data no decision has touched.
- New places and new people test the generalisation the panel will ask about.

## How to implement

1. Recording plan with dates and places; consent forms.
2. Annotation with the frozen annotation guide; agreement check on one
   session.
3. QA written and hashed before Step 03 (file hash in the protocol).
4. Manifest entries with `split: final_v3`.

## Open decisions

- **Size vs time.** Options: (a) minimum sizes above; (b) double the objects
  hours for tighter intervals; (c) as much as fits in the available weeks,
  never below the minimum. Decided when the defense date is known.

## You test this

1. Record the sessions (main work); then write your share of the questions
   without opening the app.

## How this number could be lying

- The developer still records the objects sessions; other people's questions
  and new places reduce, not remove, this bias. Stated in the limitations.

## Verification

- [ ] Minimum sizes met (or shortfall stated); consent filed.
- [ ] Annotations validated; agreement on one session.
- [ ] QA hashed before any system run; authorship tagged.

## Files changed

- [NEW] `data/scenarios_v1/final_v3/...` (git-ignored), manifest entries
- [NEW] `docs/results/phase-8/dataset-v3.md`

## Dependencies

- Step 01.

## Common issues

- Recording in public places with bystanders; follow the privacy rules (stop
  or mark exclusions).
