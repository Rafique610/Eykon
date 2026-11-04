# Phase 6.5 Step 09 — Evaluation and the Ethics Section for the Panel

## What

1. **Evaluation** on consented data only: face detection and grouping
   (Steps 03–05), voice naming (Step 06), linking (Step 07), person questions
   accuracy (Step 08, at least 30 questions if data allows, otherwise stated),
   deletion verification, cost on both phones (descriptor computation per
   keyframe, battery impact with the feature on vs off).
2. **Ethics section** for the thesis and the defense: the Step 01 design, what
   was actually implemented, test evidence for each principle (opt-in, local,
   consent-gated naming, bystander expiry, deletion), known risks that remain,
   and what a real product would still need.
3. **Scope report**: what was done inside the time box and what was not.

## Why

- A stretch feature is only worth including if it is evaluated and its
  ethics are explained; otherwise it is a liability at the defense.

## How to implement

1. Results document `docs/results/phase-6.5/results.md` with generated tables.
2. Ethics section `docs/results/phase-6.5/ethics-section.md`, written for the
   panel in plain language.
3. Supervisor review.

## Open decisions

- **Demo at the defense.** Options: (a) no live people demo (show recorded
  results only) — safest; (b) live demo with a consenting friend present;
  (c) decided with the supervisor.

## You test this

1. Read the ethics section aloud; time it (aim for 2 minutes in the defense).
2. Ask a friend to play a panel member and attack the design.

## How this number could be lying

- Small consented samples; every number states its sample size and is framed
  as a feasibility result.

## Verification

- [ ] Evaluation tables with sample sizes.
- [ ] Ethics section with evidence per principle.
- [ ] Scope report and supervisor review.

## Files changed

- [NEW] `docs/results/phase-6.5/results.md`, `ethics-section.md`
- [MODIFY] `README.md`

## Dependencies

- Step 08.

## Common issues

- Running out of time inside the box: write the scope report with what exists;
  do not extend the box without the supervisor.
