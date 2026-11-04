# Phase 7 Step 09 — Recommendation and Thesis Chapter

## What

1. **Recommendation**: the preferred split for glasses (and for a phone in a
   pocket with glasses as camera), with the trade-off table (bandwidth,
   glasses energy, phone energy, latency, accuracy) and the conditions under
   which a different split would win (from the sensitivity analysis).
2. **Thesis chapter draft** `docs/results/phase-7/chapter-draft.md`: research
   problem P4, method (routes, measurements, model), results, limitations
   (phone-as-glasses, projections), future work.
3. **Annotations**: master roadmap (P4 outcome), Phase 8 overview (what is
   claimed about glasses).

## Why

- Phase 7 is stretch; its value for the thesis is a clear, honest answer to
  P4, even if the answer is "S3 over BLE is the only realistic option for
  current low-power glasses, at the cost of no thumbnails".

## How to implement

1. Tables generated from Steps 02–08 results.
2. Chapter written in plain language with every number linked to its source.
3. Supervisor review.

## Open decisions

- **How much of Phase 7 goes into the defense slides.** Options: (a) one slide
  (stretch result); (b) a short section; (c) none if Phase 7 was cut to R3 with
  weak validation.

## You test this

1. Explain the recommended split in one minute, including what the glasses
   would and would not do.

## How this number could be lying

- Recommendations from emulation are provisional; the chapter says what would
  need to be re-measured on real glasses.

## Verification

- [ ] Recommendation with trade-off table and conditions.
- [ ] Chapter draft with sources and limitations.
- [ ] Roadmap and Phase 8 annotated.

## Files changed

- [NEW] `docs/results/phase-7/recommendation.md`, `chapter-draft.md`
- [MODIFY] `docs/plans/00-roadmap.md`, `docs/plans/phase-8-final/00-*.md`

## Dependencies

- Steps 06–08.

## Common issues

- Over-claiming from a single route; state the route used in every
  conclusion.
