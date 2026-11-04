# Phase 4.1 Step 05 — Crop Matcher v2: Templates, Personal Embeddings, Unknown Objects

## What

Improve the Probe B crop matcher into the component that answers "which of
my objects is in this hand?":

- **Crop policy**: crop size scaled to hand size, a second "below the hand"
  crop for put-down confirmation, padding at image edges.
- **Scoring**: combine (a) text-prompt similarity (several templates
  averaged) and (b) similarity to the user's enrolled prototypes (Step 03),
  with a tuned weight.
- **Decision**: top-1 object if its score is above a threshold **and** above
  the second-best by a margin; otherwise `uncertain`. Objects not in the list
  produce `unknown_object` with the crop saved (for later naming), if the
  hand is clearly holding something.
- **Calibration**: map raw scores to a confidence between 0 and 1 that
  actually predicts correctness (checked on held-out frames).
- **Experiments**: identification accuracy per object size, with and without
  prototypes, by number of enrolment photos, and by template set.

## Why

- Object identity is where Probe B most likely struggled (look-alikes,
  small objects). This step is the main lever for accuracy.
- The margin rule and the `uncertain` output stop the system from confidently
  naming the wrong object; Phase 5's ledger needs honest confidence to decide
  when to trust a state change.
- Measuring the value of personal enrolment answers a design question for the
  app (is the extra user effort worth it?).

## How to implement

1. **Evaluation set**: from the tuning sessions' annotations, take frames
   within ±1 s of annotated pick-up / put-down events where the object is
   visible, plus negatives (hands holding nothing or non-vocabulary items).
   At least 30 positives per size class where the data allows; counts
   reported.
2. **Crop policy**: implement and compare 2–3 crop scales; keep the best.
3. **Templates**: compare object name only, "a photo of a hand holding a
   {object}", and an average of 5 templates; record the winner.
4. **Prototypes**: score = w × text + (1 − w) × max prototype similarity;
   sweep w on the tuning split of the evaluation set; freeze.
5. **Threshold and margin**: chosen for a target precision (from the Step 01
   targets), reporting the recall that results.
6. **Calibration**: simple binning (reliability table) and, if clearly
   miscalibrated, a one-parameter logistic fit (numpy).
7. **Unknown objects**: when the hand is closed (Step 04 grasp state) but no
   object passes, emit `unknown_object` with the crop path; count how often
   it happens and what the objects actually were.

## Open decisions

- **Prototype aggregation.** Options: (a) max similarity over prototypes —
  robust to one good view; (b) mean of prototypes — smoother, can blur
  distinct views; (c) mean of top-2 — middle ground.
- **What to do with `uncertain`.** Options: (a) drop — fewer false events,
  more misses; (b) pass to the state machine with low confidence and let it
  combine several frames — likely best, more logic in Step 09; (c) send the
  crop to the VLM (hybrid, Step 14) — accurate, costs a VLM call.

## You test this

1. Look at the per-object confusion table. Which of your objects get mixed up
   with which? Is that what you would expect?
2. Re-enrol one confused object with 5 better photos and re-run the
   evaluation for that object. Did it help?
3. Look at 10 `unknown_object` crops and name them. Should any of them be
   added to your list?

## How this number could be lying

- Evaluating on frames near annotated events that a human could see is easier
  than live frames chosen by the pipeline; Step 12 measures end-to-end.
- Tuning w, templates and threshold on the same frames that are then
  reported inflates accuracy; the evaluation set is split into tuning and
  test parts by session, and only the test part is reported.
- With only 3–5 objects per session, accuracy looks high; the full user list
  (all objects from all sessions) is used as the candidate set.

## Verification

- [ ] Evaluation set built by script with counts per size class and object.
- [ ] Crop scale, templates, w, threshold and margin frozen from the tuning
      part.
- [ ] Test-part accuracy per size class, with and without prototypes, and by
      number of enrolment photos.
- [ ] Reliability table before and after calibration.
- [ ] `unknown_object` rate reported.

## Files changed

- [MODIFY] `src/perception/crop_match.py`
- [NEW] `src/perception/calibrate.py` (if needed)
- [MODIFY] `src/config.py`
- [NEW] `docs/results/phase-4.1/step05-crop-matcher.md`
- [MODIFY] `Taskfile.yml`, `README.md`

## Dependencies

- Step 03 (vocabulary and prototypes), Step 04 (hands and grasp state).

## Common issues

- Text embeddings computed with a different model version than image
  embeddings: always from the same frozen file.
- Crops dominated by the hand itself: try a crop shifted towards the
  fingertips.
