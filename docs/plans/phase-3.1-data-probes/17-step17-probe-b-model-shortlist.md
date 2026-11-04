# Phase 3.1 Step 17 — Probe B Shortlist: Hand, Detector, Tracker and Image-Text Models

## What

Research and verify the candidate models for the cheap, LLM-free perception
path. For each candidate, fill a row in `docs/results/phase-3.1/model-shortlist-vision.md`
and the licence ledger:

- what it does and its input / output,
- licence as stated in the licence text itself (not a summary), and whether
  it allows shipping inside an app,
- whether a **phone-ready version exists** (a `.tflite` / LiteRT model, an
  ONNX model that runs with ONNX Runtime Mobile, or an official Android
  library), with the exact file name and where it is published,
- model size on disk, and reported speed if the source states one (marked
  "reported by source, not measured"),
- whether it runs on the laptop with dependencies already installed or needs
  a new one (new dependencies need the user's approval),
- a one-line verdict: shortlisted / rejected (why).

Candidate families to check (names are starting points for research, not
choices; every licence and phone-version claim below is **to be verified**):

- **Hand landmarks / hand detection**: MediaPipe Hand Landmarker (Google; has
  an official Android Tasks library and a `.task` model file).
- **Image-text embedding (for matching a hand crop against object names)**:
  CLIP-family models such as SigLIP, MobileCLIP, and OpenCLIP small
  variants; check which have a mobile export and what licence the weights
  use (code and weights can have different licences).
- **Small object detectors (closed vocabulary)**: YOLO-family releases (some,
  such as Ultralytics releases, are AGPL-3.0, which has strong obligations
  for an app — verify the exact version), YOLOX, NanoDet, EfficientDet-Lite
  (TensorFlow Lite model maker family), RT-DETR variants.
- **Open-vocabulary detectors**: OWL-ViT / OWLv2, Grounding DINO small,
  YOLO-World — check licences and whether any phone version exists at all
  (several are likely too heavy for a phone; that is a valid reason to
  reject).
- **Trackers** (for Phase 4.1, listed now so licences are known): simple
  IoU / Kalman trackers (SORT-style, can be written in a few lines),
  ByteTrack (check licence).
- **Place recognition** (for Phase 4.1): reuse the image-text embedding
  model's image embeddings, clustered; no extra model if possible (Ponytail).

## Why

- Probe B is only fair if the cheap path uses models that could really ship
  on the phone. A laptop-only model would make the cheap path look better
  than any phone version could be.
- Licences are a hard filter. The handoff doc explicitly warns that popular
  detector releases are AGPL. Finding that out after building Phase 4.1
  around one would be expensive.
- Choosing by "has a verified phone artifact and a usable licence" first,
  and by accuracy second, follows the roadmap's Phase 4 risk rule (Tier 1
  model must have a verified mobile artifact).

## How to implement

1. **Hard filters** (in this order): licence allows research use and app
   shipping (or is clearly marked research-only and rejected for the app);
   a phone-ready file exists; size on disk under a budget (see open
   decision); runs offline.
2. **Research each candidate** from primary sources: the licence file in the
   official repository, the official model card, the official Android
   documentation. Record the URL and the date read.
3. **Laptop check**: for shortlisted models only, run each once on 5 probe
   frames to confirm it loads and produces output, using already installed
   packages where possible (OpenCV's DNN module can run some ONNX models
   without new dependencies). If a new package is needed (for example
   `mediapipe` or `onnxruntime`), list it and ask the user before adding it
   with `uv add`.
4. **Pick the Probe B stack**: one hand model, one image-text model, and
   optionally one closed-vocabulary detector as a second cheap variant.
   Record why each was chosen and what was rejected.
5. **Update the licence ledger** for every row (shortlisted and rejected).

## Open decisions

- **Detector strategy for Probe B** (handoff §6, decided after Probe B, but
  the candidates are chosen here). Options: (a) hand-centred crop matching
  only (hand model + image-text embeddings) — no training, open to a
  user-editable object list, weak on tiny objects; (b) add a small
  closed-vocabulary detector — strong on common objects (cup, phone, bag),
  but its fixed classes may not include keys or pills, and fine-tuning needs
  labelled boxes; (c) open-vocabulary detector — flexible names, probably too
  heavy for phones (to be verified). The draft shortlists (a) as the main
  path and (b) as a variant.
- **Model size budget on the phone.** Options: (a) under 50 MB total for the
  cheap path — keeps it truly cheap next to the 2.6 GB Gemma model; (b)
  under 200 MB — allows a stronger image-text model; (c) no fixed budget,
  report size and let Probe B decide. The roadmap's RAM ceilings (3.5 GB
  flagship / 2.0 GB low end, §4.1) apply to everything loaded at once.
- **Adding `mediapipe` / `onnxruntime` to the laptop environment.** Options:
  (a) add the official package — fastest, matches the phone library;
  (b) OpenCV DNN only — no new dependency, may not support every model;
  (c) add only `onnxruntime` and export models to ONNX — one runtime for all
  candidates. Needs the user's approval in any case.

## You test this

1. Read the shortlist table. Pick two rows and check the licence yourself by
   opening the licence link. Does it say what the row says?
2. For the chosen hand model, watch the 5-frame laptop check output (hand
   landmarks drawn on the frame). Are the hands found?
3. Approve or reject any new dependency the step asks for.

## How this number could be lying

- "Reported speed" from a model card is usually measured on a flagship phone
  with a GPU or NPU delegate, at a small input size. It is never used as our
  number; Step 22 measures ours.
- A licence summary on a third-party website may be outdated. Only the
  licence text counts.
- A model that "has an Android demo" may only run through a cloud API. The
  phone-ready check requires an on-device file.

## Verification

- [ ] Shortlist table with every candidate family above, each with licence
      source and date, phone artifact (file name and source), size, verdict.
- [ ] Licence ledger updated for all rows.
- [ ] Chosen Probe B stack recorded with reasons.
- [ ] Laptop load check passed for each chosen model.
- [ ] Any new dependency approved by the user before being added.

## Files changed

- [NEW] `docs/results/phase-3.1/model-shortlist-vision.md`
- [MODIFY] `docs/results/phase-3.1/licence-ledger.md`
- [MODIFY] `pyproject.toml` / `uv.lock` — only if the user approves a new
  dependency
- [MODIFY] `README.md`

## Dependencies

- Step 03 (licence ledger). Can run in parallel with all data steps.

## Common issues

- Model weights and code under different licences (permissive code,
  restrictive weights). Record both.
- MediaPipe's Python package may lag behind the Android library in model
  versions. Use the same `.task` file on both sides.
- Image-text models trained on web photos struggle with first-person,
  close-up, motion-blurred crops. That is exactly what Probe B measures; it
  is not a reason to reject a model in this step.
