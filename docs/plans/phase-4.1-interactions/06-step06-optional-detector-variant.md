# Phase 4.1 Step 06 — Optional Closed-Vocabulary Detector Variant

## What

Test whether adding a small object detector (from the Step 02 frozen set,
with a verified licence and phone artifact) improves the cheap path enough to
keep it:

- run the detector on the same evaluation frames as Step 05 (and on full
  frames, not only hand crops),
- map detector classes to the user's object list (only some objects will
  have a matching class — e.g. "cell phone", "cup", "handbag", "book"; keys or
  pills may have none),
- combine: detector box overlapping the hand → candidate object; crop matcher
  confirms or overrides,
- measure accuracy gain per object and cost per frame on laptop (and on the
  phone from Phase 3.1 Step 22 numbers, then Step 15),
- decide: keep (for which objects), or drop with the numbers.

Skip this step entirely if Step 01 chose reduced scope or Step 02 decided
"no detector".

## Why

- The supervisor suggested object detection; this step gives a measured
  answer instead of an opinion.
- Detectors are often strong for common medium / large objects and weak or
  blind for the small personal items users actually lose. Knowing exactly
  where the line falls tells us when the detector is worth its cost.
- Detectors also give boxes for objects **not** in hand (a bag on a chair),
  which helps place and "last seen" answers; that benefit is measured
  separately.

## How to implement

1. **Wrapper** `src/perception/detector.py`: `detect(frame) -> list[Box]`
   with class, score; same preprocessing constants as the phone.
2. **Class mapping** table in the vocabulary (Step 03): `detector_class`
   optional per object; objects without a class are scored by crop matching
   only.
3. **Fusion rule**: if a detector box of a mapped class overlaps the hand
   crop and its score is high, boost that object's score in the crop matcher;
   if the detector sees a mapped object **not** in hand, emit an
   `observation` slot record (for "last seen").
4. **Experiments**: Step 05 test part — crop only vs crop + detector, per
   object; cost per frame; and the "last seen" benefit on put-down events
   (is the object detected on the surface after release?).
5. **Decision** written in the results doc with numbers.

## Open decisions

- **Fine-tuning the detector on our objects.** Options: (a) no — use the
  pre-trained classes only (draft); (b) fine-tune on a few hundred labelled
  boxes of our objects — likely a big gain for keys and wallets, costs
  labelling time and risks overfitting to our objects; (c) only if the
  pre-trained variant shows promise for medium objects and the timeline
  allows.
- **Run rate.** Options: (a) every cascade frame; (b) only when a hand is
  present; (c) only on put-down confirmation frames. Cost decides; (b) or (c)
  likely.

## You test this

1. Watch the detector debug view on the kitchen session. Which of your
   objects does it ever detect? Which never?
2. Read the keep / drop decision and its numbers. Do you agree that the gain
   is (or is not) worth the extra model on your phone?

## How this number could be lying

- Detector classes that match common household items make kitchen sessions
  look good; per-object reporting shows that keys or pills may have no
  detection at all.
- A detector licence or phone artifact can look fine for the base model but
  not for an exported variant; the exact file used is the one in
  `model-set.md`.

## Verification

- [ ] Wrapper, class mapping and fusion implemented (or step skipped with
      the reason).
- [ ] Per-object accuracy with and without detector on the Step 05 test part.
- [ ] Cost per frame on laptop; phone cost from Phase 3.1 Step 22.
- [ ] "Last seen" benefit on put-downs measured.
- [ ] Keep / drop decision recorded.

## Files changed

- [NEW] `src/perception/detector.py`
- [MODIFY] `src/perception/crop_match.py` (fusion), `src/perception/vocab.py`
  (class mapping)
- [NEW] `docs/results/phase-4.1/step06-detector.md`
- [MODIFY] `Taskfile.yml`, `README.md`

## Dependencies

- Step 02 (frozen detector, licence), Step 05 (crop matcher and evaluation
  set).

## Common issues

- AGPL-licensed detector releases: excluded in Step 02; do not swap one in
  here for a quick test that later ends up in the app.
- Detector input sizes differ from crop sizes; run it on the full 640×480
  frame, not on crops.
