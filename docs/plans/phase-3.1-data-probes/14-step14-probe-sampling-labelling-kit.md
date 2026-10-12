# Phase 3.1 Step 14 — Probe Sampling and Blind Labelling Kit

## What

Build the two small tools all probes share:

1. **Stratified frame sampler** `src/probes/sample.py`: picks probe frames
   from tuning sessions by script, with a fixed seed, filling the cells
   defined in the pre-registration (object size × lighting for Probe A).
   Writes `data/probes/a/frames.json` (frame path, session, time, cell) and
   copies the frames into `data/probes/a/frames/`.
2. **Blind labelling page** `src/probes/label_app.py`: a separate Streamlit
   page (not added to the 458-line `src/ui/app.py`) that shows a frame next
   to one model output at a time, with the model name and prompt hidden and
   the order shuffled, and records the label.
3. **Frame truth labels**: before any model output is shown, the labeller
   lists the vocabulary objects actually visible in each probe frame (with
   size class and an optional box). This is the reference for misses.
4. **Labels format** `data/probes/<probe>/labels.jsonl`: one line per label
   with labeller id, item id, label, time spent, timestamp.
5. **Double-labelling**: a fixed 20 % subset is labelled by a second person
   (or the user again after a week) for agreement.

## Why

- Hand-picked frames make results look better or worse depending on the
  picker's mood. A seeded script makes the sample reproducible and neutral.
- If the labeller sees "Gemma, slot prompt" next to the output, their
  judgement is influenced by what they expect from that model. Hiding it is
  cheap and removes an obvious panel objection.
- Labelling "what is truly in the frame" **before** seeing any model output
  avoids anchoring: once you read "a red mug on the desk", you start seeing a
  red mug.
- A separate page keeps the main app small and avoids growing a file that is
  already over the 300-line rule.

## How to implement

1. **Candidate frames**: from `frames_1fps/` of tuning sessions only
   (`split_v1.json`), excluding `exclude` ranges.
2. **Cell assignment**:
   - lighting comes from the manifest per session (`bright` / `normal` /
     `dim`), optionally refined by mean frame brightness computed with
     OpenCV (already installed); the rule is written in the
     pre-registration;
   - object size: a frame belongs to the "small" cell if, according to the
     annotation, a small vocabulary object is within 2 seconds of a short
     event at that time (so the object is likely in view); similarly for
     medium and large. Frames with no nearby event fill an "any" pool used
     for invention measurement.
3. **Sampling**: `random.Random(seed)` (standard library), at least 20
   frames per cell, total at least 120. The seed and the candidate counts per
   cell are written into `frames.json`.
4. **Labelling page flow**:
   - Pass 1, truth: frame only → tick visible vocabulary objects, mark
     size, optional box drag (Streamlit image click helpers only if already
     available; otherwise skip boxes, as decided in Step 09).
   - Pass 2, outputs: frame + one anonymised model output → for each object
     mentioned: `correct` / `invented` / `wrong_attribute` (exists but the
     colour, place or state is wrong); for the whole output: `correct` /
     `partly` / `wrong`, using written criteria.
   - Keyboard-friendly, saves after every item, can resume.
5. **Second labeller**: the page takes a labeller id; the 20 % subset is
   chosen by seed.
6. **Agreement**: Cohen's kappa (agreement beyond chance between two
   labellers) for the per-object labels, computed in `src/probes/common.py`
   with the standard library.

## Open decisions

- Second labeller identity: phase overview open decision (friend or
  classmate / user a week later / supervisor spot check).
- **Labelling unit.** Options: (a) per object mention — precise invention
  rate, more clicks; (b) per whole output (correct / partly / wrong) —
  fast, less precise; (c) both, as drafted — most informative, slowest.
- **Truth labels on all 120 frames or only a subset.** Options: (a) all —
  miss rate on the full sample; (b) only the size cells — saves time, no
  miss rate on the "any" pool; (c) all, but objects limited to the
  vocabulary — the draft.

## You test this

1. Run `task probe-sample -- a` twice. The two `frames.json` files must be
   identical (same seed, same frames).
2. Open `task probe-label -- a`. Label 10 frames in pass 1. Time yourself.
3. In pass 2, try to guess which model produced each output. If you can
   guess easily (for example from the writing style), note it — blinding is
   then only partial and must be reported.

## How this number could be lying

- Cell assignment by "near an annotated event" misses frames where the
  object is visible but not being moved. Those frames go to the "any" pool;
  the report says so.
- Blinding is partial if outputs have recognisable styles (slot JSON vs
  free text). Outputs can be normalised to the same plain list of objects
  before showing; whether this is done is recorded.
- Labeller fatigue: labels in the last third of a session are compared with
  the first third.

## Verification

- [ ] Sampler is deterministic (same seed, same output) and fills every
      cell with at least 20 frames, or reports why a cell cannot be filled.
- [ ] Labelling page hides model identity and shuffles order; resumes after
      restart.
- [ ] Truth pass is enforced before output pass for each frame.
- [ ] Kappa function checked on a small hand example.
- [ ] `label_app.py` and `sample.py` each under 300 lines; `src/ui/app.py`
      unchanged.

## Files changed

- [NEW] `src/probes/sample.py`, `src/probes/label_app.py`
- [MODIFY] `src/probes/common.py` — kappa
- [NEW] `data/probes/a/` (git-ignored)
- [MODIFY] `Taskfile.yml` — `probe-sample`, `probe-label`
- [MODIFY] `README.md`

## Dependencies

- Step 13 (pre-registration defines cells and sample sizes).
- Step 10 for the size cells (annotated events). The truth pass can start
  with bright/dim cells before Step 10 is complete.

## Common issues

- Dim cells are hard to fill if few dim sessions were recorded; Step 07's
  low-light session is the main source. If it is too short, record a second
  one rather than lowering the cell size.
- Streamlit reruns the whole script on every click; keep label state in
  `st.session_state` and write to disk immediately.
