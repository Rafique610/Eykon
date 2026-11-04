# Phase 5.2 Step 14 — Mobile Parity Gate 5.2 (Answer Layer on Pixel + Infinix)

## What

Prove the answer layer gives the same answers on the phones as on the laptop
for the deterministic levels, and comparable answers for the generative ones:

1. **Golden questions**: 60 questions (stratified over the 11 categories)
   with laptop answers frozen per configuration, using the configuration
   databases pushed to both phones.
2. **Agreement**:
   - levels T and Q: identical answer text and evidence ids (deterministic);
   - level X: same span (or overlapping span) in at least a high share of
     questions (threshold below);
   - level G: same correctness judgement and valid citations, compared by the
     scorer and a human look on disagreements (text will differ).
3. **End-to-end latency** P50 / P90 from tap to answer on both phones per
   configuration (from Step 11, re-checked here with the final UI).
4. **Airplane-mode check**: all levels work with no network; network logging
   shows zero calls.

## Why

- Roadmap §4: every phase ends with a phone exam. The answer layer is what
  the user sees; if the phone answers differently from the laptop results the
  thesis reports, the results do not describe the product.
- Deterministic levels must match exactly; any difference is a port bug and
  is cheap to find with golden questions.

## How to implement

1. `task push-golden-answers` pushes questions, expected answers and
   databases.
2. Instrumented test runs all golden questions per configuration and writes
   `parity_report.json`.
3. Differences classified: port bug (fix), tokenizer / float difference
   (explain), generative variation (expected, scored).
4. Network logging during the run (Phase 6 Step 07 method, used early here in
   its simple form).

## Open decisions

- **Level X agreement threshold.** Options: (a) at least 95 % same span;
  (b) at least 90 % overlapping span; (c) set from laptop run-to-run
  variation (draft).

## You test this

1. Run the golden questions on the Infinix in L0; then ask 5 of them by hand
   and compare with the laptop answers.
2. Check the network log shows nothing during the run.

## How this number could be lying

- 60 golden questions are a subset; Step 09's full run is laptop-based. The
  agreement rate here is how much the laptop results can be trusted for the
  phone.

## Verification

- [ ] T and Q identical on both phones for all golden questions (or every
      difference explained and fixed).
- [ ] X and G agreement measured against chosen thresholds.
- [ ] End-to-end latency per configuration on both phones.
- [ ] Zero network calls confirmed.

## Files changed

- [NEW] `android/.../answers/` instrumented tests
- [NEW] `docs/results/phase-5.2/parity-report.md`
- [MODIFY] `Taskfile.yml`, `README.md`

## Dependencies

- Steps 11, 13.

## Common issues

- Date and time formatting differs by phone locale; templates use a fixed
  format in evaluation mode.
