# Phase 3.1 Step 20 — Probe C Shortlist: VAD, Speech Recognition and Speaker Models

## What

Research and verify candidate models for the on-device speech path, the same
way Step 17 does for vision. One table,
`docs/results/phase-3.1/model-shortlist-speech.md`, plus licence ledger rows:

- **Voice activity detection (VAD)** — finds the parts of the audio that
  contain speech, so heavier models skip silence. Candidates to verify:
  Silero VAD, WebRTC VAD, the VAD built into sherpa-onnx.
- **Speech recognition (ASR)** — English only (planning default). Candidates
  to verify: Whisper tiny.en and base.en through whisper.cpp (the Android app
  already expects `ggml-tiny.en.bin` / `whisper-tiny.en.tflite`, see below),
  sherpa-onnx streaming and non-streaming English models, Vosk small English.
- **Speaker embeddings and diarization (who spoke when)** — candidates to
  verify: sherpa-onnx speaker embedding models (several published
  embedding models are exported for it), pyannote (laptop reference only;
  check model access conditions), WeSpeaker, NeMo TitaNet-small (check for a
  mobile export).
- **"Me vs others"**: compare each speech segment's embedding with the
  user's enrolment embedding (Step 08's 30-second sample); no extra model.

For each: what it does, licence of code and of weights (from the licence
text), phone-ready artifact (file, runtime), size, laptop runnability with
existing dependencies, verdict.

## Why

- Probe C and Phase 5.1 depend on these choices. As with vision, a model
  without a phone version or with an unusable licence cannot be part of the
  shipped system, so it must not be the one that makes Probe C look good.
- **The current Android speech path is not really on-device.** Two facts
  from the code:
  1. `WhisperTranscriber.kt` resolves a Whisper model file but its
     `transcribe` function does **not** run inference: it returns the text
     `"Voice memo (N s recorded)"` (a placeholder comment says "binds to the
     TFLite / ONNX Whisper session in full production"). Phase 2 Step 05 is
     marked done, but on-device transcription is not implemented.
  2. `NativeSpeechRecognizer.kt` uses Android's `RecognizerIntent`, which on
     many devices uses an online recogniser (roadmap §9 item 1).
  So today there is no verified offline speech recognition on the phone.
  This step picks what replaces it. (Update 07 October 2026: the user
  downloads the offline Whisper model file to the phone. The model file is
  not the gap; the missing piece is the code that loads it and runs
  inference inside `transcribe()`. Phase 5 Step 04 implements that call with
  the runtime chosen here.)
- Diarization is the least mature part on phones. Knowing early what exists
  (and what does not) decides how ambitious Phase 5.1's "who said what" can be.

## How to implement

1. **Hard filters**: offline; licence allows research and app use; phone
   artifact exists (whisper.cpp builds for Android, ONNX models for
   sherpa-onnx, `.tflite` files); English model available.
2. **Primary sources only** for licences and artifacts (official repos,
   model cards, licence files), with URLs and dates.
3. **Laptop check** for shortlisted items: transcribe 1 minute of a pilot
   meeting; run VAD on it; extract speaker embeddings for 3 segments of 2
   speakers and check that same-speaker similarity is higher than
   different-speaker similarity. New dependencies (for example
   `sherpa-onnx`, `pywhispercpp`, `onnxruntime`) only with user approval.
4. **Laptop reference system**: one stronger, laptop-only configuration is
   allowed as an **upper bound** and for pre-filling annotations (Step 09),
   clearly labelled "not shippable". It must not be the same model as the
   one under test in Probe C.
5. **Choose the Probe C stacks**: at least two ASR sizes (for example tiny
   and base), one VAD, one speaker embedding model plus a simple clustering
   method (agglomerative clustering on embeddings with a distance threshold,
   written with numpy, which is already installed).
6. **Note for Phase 2 / Phase 5**: add an annotation to
   `docs/plans/phase 2/✅ 05-step05-whisper-capture.md` saying that
   on-device transcription is a placeholder in the code, pointing to this
   step and to Phase 5 Step 04 (annotation only, nothing deleted).

## Open decisions

- **ASR family.** Options: (a) whisper.cpp tiny.en / base.en — matches the
  file names the app already expects, good accuracy for size, not
  streaming (processes chunks); (b) sherpa-onnx streaming models — real-time
  partial results, one runtime that also covers VAD and speaker embeddings;
  (c) both in Probe C, choose by measured WER and real-time factor.
- **Diarization approach.** Options: (a) embeddings per VAD segment +
  clustering (our own few lines) — light, transparent, weak on overlap;
  (b) a packaged diarization pipeline (sherpa-onnx offers one; to be
  verified) — less code, less control; (c) laptop-only pyannote as an upper
  bound plus (a) on the phone — shows the gap between best and shippable.
- **Number of speakers known in advance?** Options: (a) yes, the user says
  "4 people" when starting a session — much easier clustering, small UX cost;
  (b) no, estimated automatically — harder, more realistic; (c) both
  measured in Probe C.

## You test this

1. Read the shortlist; check the licence of one ASR and one speaker model
   yourself.
2. Listen to the 1-minute laptop transcription next to the audio. Note
   errors in names and numbers specifically (these matter most for
   meetings).
3. Confirm you understand the finding about `WhisperTranscriber.kt` and
   decide whether it should be fixed now or as part of Phase 5 Step 04
   (it is flagged, not silently fixed).

## How this number could be lying

- Published WER numbers are usually on clean read speech (audiobooks),
  far easier than a phone on a table in a meeting. Never used as our
  numbers.
- A same-speaker similarity check on 3 segments says nothing about 4
  similar voices in a noisy room. It is a load check only.
- "Real-time on phone" claims from model cards depend on the phone and
  thread count. Step 22 measures ours.

## Verification

- [ ] Shortlist table for VAD, ASR, speaker models with licences,
      artifacts, sizes, verdicts.
- [ ] Licence ledger updated.
- [ ] Laptop checks passed for chosen items; any new dependency approved.
- [ ] Laptop reference (upper bound) chosen and labelled not shippable.
- [ ] Phase 2 Step 05 doc annotated about the placeholder transcriber.
- [ ] User informed about the placeholder and the online recogniser.

## Files changed

- [NEW] `docs/results/phase-3.1/model-shortlist-speech.md`
- [NEW] `src/speech/__init__.py`, `src/speech/vad.py`, `src/speech/asr.py`,
  `src/speech/speakers.py` (thin wrappers for the chosen models)
- [MODIFY] `docs/results/phase-3.1/licence-ledger.md`
- [MODIFY] `docs/plans/phase 2/✅ 05-step05-whisper-capture.md` (annotation)
- [MODIFY] `pyproject.toml` / `uv.lock` — only with approval
- [MODIFY] `README.md`

## Dependencies

- Step 03 (licence ledger). Can run in parallel with the data steps.

## Common issues

- whisper.cpp on Windows needs a prebuilt wheel or binary; building from
  source needs Visual Studio build tools (tooling.md rule: use prebuilt
  binaries).
- Whisper models produce text for silence ("Thank you." on empty audio). VAD
  before ASR prevents most of it; count it when it happens.
- Speaker embedding models expect 16 kHz mono; resample once at extraction
  (Step 07/08), not inside every wrapper.
