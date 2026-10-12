# Phase 6.5 Step 07 — Face–Speaker Linking with Honest Failure Reporting

## What

Try to connect "who is visible" with "who is speaking", so a named face can
name a voice (or the other way round), and measure how often it works:

- **Signal**: when exactly one named face is visible in keyframes during a
  speech segment from a single speaker cluster, count a co-occurrence; after
  enough co-occurrences, propose a link "this voice is probably Alex".
- **User confirmation** required before a link is used for naming.
- **Measurement** on consented sessions with video: share of speech segments
  where any face is visible at all, correct link proposals, wrong proposals,
  time to the first correct proposal.

## Why

- Roadmap v2 says this "is hard from a chest or head camera and will be
  reported with its failures". The point of this step is an honest
  measurement, not a polished feature.
- The co-occurrence approach is simple and transparent; lip-movement based
  speaker detection is out of scope (heavier models, privacy).

## How to implement

1. `src/people/linking.py`: co-occurrence counts per (face group, speaker
   cluster) over sessions; proposal rule with minimum counts and dominance.
2. Confirmation UI (one question in the review screen).
3. Evaluation script; failure list by cause: face not visible (camera pointed
   elsewhere), several faces visible, user speaking (own face never visible),
   wrong cluster.

## Open decisions

- **Minimum evidence.** Options: (a) 3 co-occurrences; (b) 10; (c) dominance
  ratio rule (most co-occurrences at least twice the next). Draft: (c) with a
  minimum of 3.

## You test this

1. In a consented meeting with video, check which links were proposed. Were
   they right?

## How this number could be lying

- A chest camera facing one person across a table makes linking easy;
  multi-person meetings are the real test; both reported.

## Verification

- [ ] Linking proposals with confirmation; never automatic naming.
- [ ] Visibility share, correct / wrong proposals, failure causes reported.

## Files changed

- [NEW] `src/people/linking.py`, review UI changes
- [NEW] `docs/results/phase-6.5/step07-linking.md`
- [MODIFY] `README.md`

## Dependencies

- Steps 05, 06.

## Common issues

- The user's own voice dominates co-occurrence counts with whoever they look
  at; exclude "me" segments.
