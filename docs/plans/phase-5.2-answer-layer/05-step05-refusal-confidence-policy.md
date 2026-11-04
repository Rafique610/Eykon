# Phase 5.2 Step 05 — Refusal and Confidence Policy ("I Don't Know")

## What

A single policy for when the system should **not** answer, applied after every
level:

- refuse when the best evidence is below a threshold, when the time window has
  no records, when the entity was never seen, or when the generative level's
  citations fail validation;
- partial answers when evidence exists but is weak: "Last seen in your hand at
  14:02; I don't know where it was put";
- refusal wording that says what was searched ("I have no record of your
  passport since you started recording on 3 October");
- thresholds per level and intent, tuned on the tuning split for a target
  balance between wrong answers and refusals;
- measurement: `negative` category accuracy (correct refusal), false refusal
  rate on answerable questions, and the risk–coverage curve (accuracy of
  answered questions vs share answered).

## Why

- A memory assistant that confidently gives a wrong location is worse than
  one that says "I don't know". The `negative` category (Phase 3.1 Step 01)
  exists to test this.
- Small generative models tend to answer anyway; the policy makes refusal a
  system decision based on evidence, not the model's choice.
- Risk–coverage curves compare levels fairly: a level that answers less but
  more accurately is not simply "worse".

## How to implement

1. `src/answers/refusal.py`: `decide(answer, evidence, intent, level) ->
   Answer` (may convert to refusal or partial).
2. Thresholds in settings per level and intent; tuned on the tuning split
   with a target such as "at most 1 wrong answer in 10 answered" (user
   confirms the target).
3. Refusal templates with "what was searched" details (time range, sources).
4. Risk–coverage computation in the evaluation script (Step 10 / 12).

## Open decisions

- **Target trade-off.** Options: (a) favour refusing (few wrong answers, more
  "I don't know"); (b) favour answering (fewer refusals, more wrong answers);
  (c) per intent — strict for object locations, lenient for summaries. The
  user decides as the product owner.
- **Partial answers.** Options: (a) allowed (draft) — more useful; (b) never —
  simpler scoring; (c) only for object questions.

## You test this

1. Ask 10 questions about things that never happened. How many refusals?
2. Ask 10 answerable but hard questions. How many wrong refusals?
3. Choose the trade-off option for your own use.

## How this number could be lying

- `negative` questions about plausible objects are harder than about absurd
  ones; Phase 3.1 Step 01 requires plausible negatives — check a sample.
- Thresholds tuned on the tuning split may not hold on held-out; both
  reported.

## Verification

- [ ] Policy applied after every level, recorded in `Answer.refused` with a
      reason.
- [ ] Thresholds tuned on tuning split; target confirmed by the user.
- [ ] `negative` accuracy, false refusal rate and risk–coverage curves per
      level on tuning data.

## Files changed

- [NEW] `src/answers/refusal.py`
- [MODIFY] `src/config.py`, `src/answers/interface.py`
- [NEW] `docs/results/phase-5.2/step05-refusal.md`
- [MODIFY] `README.md`

## Dependencies

- Steps 03, 04 (and 06, 07 once built).

## Common issues

- Refusing because the router searched the wrong level; check routing logs
  before blaming thresholds.
