# Phase 5.1 Step 17 — Conversation Evaluation on Tuning and Held-Out Meetings (Main 5.1 Results)

## What

The main results of this phase, with the configuration frozen before the
held-out meetings are opened:

- **Data**: all tuning meetings and lecture(s), AMI subset, and the held-out
  meetings recorded in Phase 3.1 Step 08 (never processed until now). In
  total at least 10 sessions judged by humans.
- **Held-out QA**: conversation questions for the held-out meetings written
  **before** the run (by someone other than the user where possible).
- **Metrics** per category (`who_said`, `conversation_recall`,
  `action_items`, `meeting_summary`, `lecture_recall`, `negative`) and per
  answer level available at this point (L0 templates / quotes, L2
  generative): accuracy with intervals, evidence correctness (cited time
  within tolerance), refusal correctness for `negative`.
- **Stage metrics** on held-out: WER, DER, "me vs others", topic F1, action
  item precision / recall, faithfulness counts (Step 15 audit applied to
  held-out sessions too).
- **Before and after speaker naming** (Step 06) with edit counts.
- **Generalisation gap**: tuning vs held-out for every metric.
- **Verdict** against the Step 01 targets.

## Why

- Exit criteria of the phase. These are the conversation numbers that go into
  the thesis and the Phase 5.2 comparison.
- Held-out meetings with questions written in advance protect against having
  tuned thresholds (VAD, clustering, topic, support check) to the meetings we
  then report.

## How to implement

1. Freeze: `docs/results/phase-5.1/frozen-config.json` (all settings, model
   hashes) with its hash committed before processing held-out meetings.
2. Write held-out questions; record file timestamps.
3. Run the full pipeline on held-out meetings (laptop, emulation profile);
   run the Step 15 audit on their summaries.
4. Run all conversation questions through the router and answer layer at each
   level; score automatically where possible (exact speaker, set overlap,
   time tolerance) and by blind human judgement for the rest.
5. Tables by script; generalisation gap; per-session rows; failure examples.

## Open decisions

- **External LLM judge for open answers.** Options: (a) none — human only,
  slower, cleanest; (b) an external judge as evaluation tooling, labelled as
  such and cross-checked with humans on a subset (allowed by roadmap §5.1);
  (c) human for held-out, judge for tuning. Phase 3 Step 12 sets the judge
  rules; follow them if used.

## You test this

1. Ask 15 questions live about a held-out meeting on the phone (airplane
   mode) and score each answer correct / partly / wrong.
2. Read the verdict section. Is it honest about what does not work?

## How this number could be lying

- Mock meetings among friends are easier than real work meetings; AMI rows
  are the independent check.
- The user is a participant in every own meeting; questions by other authors
  and AMI questions are reported separately.

## Verification

- [ ] Frozen config hash committed before held-out processing.
- [ ] Held-out questions written before the run (timestamps).
- [ ] Per-category accuracy for each level, tuning and held-out, with
      intervals; at least 10 sessions judged.
- [ ] Stage metrics, naming before / after, generalisation gap.
- [ ] Verdict against Step 01 targets.

## Files changed

- [MODIFY] `src/benchmarks/conversation_eval.py`
- [NEW] `docs/results/phase-5.1/results.md`, `docs/results/phase-5.1/*.csv`,
  `frozen-config.json`
- [MODIFY] `README.md`

## Dependencies

- Steps 12–16.

## Common issues

- Accidentally re-tuning after seeing held-out results: any change requires
  new held-out meetings (same rule as Phase 4 Step 12).
