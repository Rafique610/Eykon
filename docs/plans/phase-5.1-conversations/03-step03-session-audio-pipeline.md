# Phase 5.1 Step 03 — Session Audio Pipeline: VAD + Chunked ASR

## What

Turn a recorded session's audio into timed text segments:

1. **VAD** splits the audio into speech segments (reusing `src/speech/vad.py`
   and the Phase 5 Step 04 Android component).
2. **Chunking** keeps segments between a minimum and maximum length (e.g. at
   most 30 s), splitting long speech at short pauses.
3. **ASR** transcribes each segment (model size chosen from Probe C), with
   word-level times where the runtime gives them and segment-level times
   otherwise.
4. **Output**: `asr.json` per session — segments with start, end, text,
   per-segment confidence (from the ASR runtime if available), and the model
   used; plus `utterances` rows with `speaker_id` still empty (filled in
   Steps 05–07).
5. **Resumable**: processing can stop and restart without redoing finished
   segments.

## Why

- Every conversation feature depends on the transcript. Doing it in VAD
  segments keeps memory flat on long sessions and skips silence (which also
  avoids the known problem of Whisper writing text for silence).
- Word-level times let the aligned transcript (Step 07) and evidence links
  (Step 09) point to the exact moment something was said.
- Resumability matters because processing runs while charging (Step 11) and
  may be interrupted.

## How to implement

1. `src/conversations/` calls the shared `src/speech/` wrappers; no second
   ASR wrapper.
2. Chunk rules in settings: minimum segment length, maximum length, padding
   around speech (e.g. 200 ms), merge gap.
3. Store progress: `asr.json` written incrementally with the last finished
   segment index.
4. Text normalisation kept separate from storage (raw ASR text stored;
   normalised only for scoring).
5. **Evaluation on tuning meetings**: WER per meeting and per condition
   (clean / noisy / overlap / placement), real-time factor, peak memory —
   compared with the Probe C numbers to confirm the pipeline matches.
6. **Android**: the same pipeline as a worker (scheduled in Step 11), using
   the downloaded Whisper model through the real runtime call (Phase 5
   Step 04 replaces the placeholder `transcribe()`).

## Open decisions

- **ASR model size per phone.** Options: (a) same model on both phones —
  parity, maybe too slow on the Infinix; (b) larger on Pixel, smaller on
  Infinix — better quality where possible, two configurations to evaluate;
  (c) user-selectable "quality vs speed" setting. Probe C real-time factors
  decide what is feasible.
- **Segment padding.** Options: (a) 0 ms — cuts word edges; (b) 200 ms —
  draft; (c) 500 ms — safer edges, more overlap between segments.

## You test this

1. Run `task session-asr -- <meeting>` on a tuning meeting and read 3 minutes
   of `asr.json` next to the audio. Note mistakes in names and numbers.
2. Stop the process halfway and restart it. It must continue, not restart.

## How this number could be lying

- WER on tuning meetings that were also used in Probe C is not new evidence;
  this step only confirms the pipeline. New evidence comes from held-out
  meetings in Step 17.
- Segment confidence from ASR runtimes is often poorly calibrated; it is used
  only as a hint until Step 15 checks it against errors.

## Verification

- [ ] `asr.json` produced for all tuning meetings; WER within the Probe C
      range (or the difference explained).
- [ ] Resumability tested.
- [ ] Real-time factor and peak memory recorded (laptop, emulation profile).
- [ ] Android worker runs on one meeting on the Pixel (full measurement in
      Step 18).

## Files changed

- [NEW] `src/conversations/transcribe.py`
- [MODIFY] `src/speech/asr.py`, `src/speech/vad.py` (chunking options)
- [NEW] `android/.../conversations/TranscribeWorker.kt`
- [MODIFY] `src/config.py`, `Taskfile.yml`, `README.md`

## Dependencies

- Step 02; Phase 5 Step 04 (on-device ASR call); Phase 3.1 Steps 20–21.

## Common issues

- Whisper hallucination on long silence or music: VAD threshold too low;
  check segments with very low audio energy.
- Times drifting over 30 minutes when segments are processed separately:
  always add the segment's start time from the original audio, never
  accumulate durations.
