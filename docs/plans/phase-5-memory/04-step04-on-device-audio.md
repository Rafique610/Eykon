# Step 04 — On-Device Audio: VAD + ASR Aligned to the Timeline

## What
Continuous microphone → voice activity detection → on-device ASR on speech
segments only → transcripts with absolute timestamps attached to the
overlapping event. Replaces the Phase 2 `RecognizerIntent` path for ambient
capture.

## Why
- Phase 2 Step 05 moved voice input to `RecognizerIntent`, which on many
  devices uses Google's **online** recogniser — incompatible with "zero network
  calls". Must be verified and replaced for ambient capture.
- Conversation recall is one of the three main use cases (LightMem-Ego,
  `new_Dev.md`), and it's impossible without aligned transcripts.

## How to implement
- Laptop: Silero VAD (ONNX) + whisper.cpp / `ggml-tiny.en.bin` (already in
  `models/`) → `src/audio/` feature folder.
- Phone: same VAD model + whisper.cpp Android JNI; verify in **airplane mode**.
- Segment rules: end on silence > 800 ms, max 30 s; timestamps from audio
  clock mapped to the shared monotonic timeline.
- Experiment: WER on 20 min of your own annotated speech (English + Urdu/mixed
  — see decision), latency per segment, CPU %.

## Open decisions
- **Language**: (a) English-only tiny.en — fastest, fails on Urdu/code-mixed;
  (b) multilingual tiny/base — handles Urdu, slower and less accurate in English;
  (c) language-detect then route — best coverage, two models.
- **ASR engine**: (a) whisper.cpp — same model both sides, mature;
  (b) Moonshine — faster on short clips, check Android support; (c) Android
  on-device `SpeechRecognizer` (offline language pack) — native, but behaviour
  varies by OEM and can't run on laptop (parity lost).

## You test this
- Airplane mode on, have a 5-min conversation with someone (with consent),
  then ask "what did they say about X?". Read the transcript and mark errors.

## How this number could be lying
- WER on clean read speech is far better than on a noisy café → record at least
  one noisy session.

## Verification
- [ ] Zero network traffic during capture (airplane-mode test + logging).
- [ ] WER table per condition; latency P50/P90 per segment on both phones.
- [ ] Transcripts linked to events with correct time overlap.

## Files changed
- [NEW] `src/audio/vad.py`, `src/audio/asr.py`, Android `audio/` package
- [MODIFY] `pyproject.toml` (VAD runtime only if needed), `README.md`

## Dependencies
- Step 03.
