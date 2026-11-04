# Phase 8 Step 07 — Limitations and Negative Results Chapter

## What

A thesis chapter that states plainly what did not work, what was not tested,
and why the results might not generalise:

1. **Negative results** gathered from all phases: probes that failed their
   pre-registered thresholds, tiers removed by ablations, configurations that
   lost, failure taxonomies (small objects, occlusion, overlap speech, noisy
   rooms, look-alikes), live-run problems, anything cut and why.
2. **Threats to validity**:
   - data: one main user, own rooms, mock meetings, consented friends;
   - measurement: laptop vs phone, replay vs live, short runs vs days, raters;
   - design: pre-registration deviations (with reasons), thresholds that had
     to change;
   - comparison: reference design not on the same benchmark.
3. **Ethics and privacy limits** (Phase 6 Step 07, Phase 6.5 if done).
4. **What a real product would still need**.

## Why

- The roadmap pessimist rules say "a negative result is a result; it goes in
  the thesis". A panel that already rejected the project once will respect an
  honest account more than a perfect-looking one.
- Naming threats before the panel does takes away their strongest questions.

## How to implement

1. Collect from every phase's results documents and "how this number could be
   lying" sections (they were written for this purpose).
2. Organise by theme, each limitation with evidence and its effect on the
   claims.
3. Supervisor review.

## Open decisions

- **Placement.** Options: (a) a separate chapter (draft); (b) a section in each
  results chapter; (c) both (short per chapter, full in one chapter).

## You test this

1. Read the chapter and add anything you know that is missing (especially
   things you avoided during the field study).

## How this number could be lying

- A limitations chapter can still hide things by omission; the checklist of
  every phase's failure list makes omissions visible.

## Verification

- [ ] Every phase's negative results and failure lists included.
- [ ] Threats to validity per theme with evidence.
- [ ] Supervisor review.

## Files changed

- [NEW] `docs/results/phase-8/limitations-chapter.md`

## Dependencies

- Step 06.

## Common issues

- Writing limitations as excuses; each one states the effect on a claim, not
  a reason it is acceptable.
