# Phase 5.1 Step 04 — Voice Enrolment for "Me"

## What

Let the system recognise the user's own voice:

1. **Enrolment**: the user records a short sample (about 30 seconds of a
   fixed paragraph, as in the Phase 3.1 recording protocol) once in the app;
   the speaker embedding model (Probe C choice) turns it into a "voiceprint"
   (an average embedding of several windows), stored locally.
2. **Matching**: in every session, each speech segment's embedding is compared
   with the voiceprint; segments above a threshold are labelled `me`.
3. **Re-enrolment**: optional additional samples (different rooms, phone on
   the table vs in a pocket) are added to the voiceprint.
4. **Evaluation**: "me vs others" accuracy (share of speech time labelled
   correctly) per condition and phone placement, on tuning meetings.

## Why

- "What did I agree to do?" and "what did I say about X?" are among the most
  useful meeting questions, and they need only one speaker to be recognised
  reliably — much easier than separating everyone.
- If Probe C said full speaker separation is unusable, "me vs others" is the
  fallback scope (overview scope rule), so it must work well on its own.
- The voiceprint also anchors the diarization in Step 05 (one known cluster).

## How to implement

1. `src/conversations/enrolment.py`: `enrol(wav_paths) -> voiceprint`,
   `is_me(segment_embedding) -> (bool, score)`; voiceprint stored in a
   `voiceprints` table (id, created_at, embedding, sample_count, model_hash).
2. **Threshold**: chosen on the pilot and tuning meetings for a target
   precision of `me` labels (wrongly calling someone else "me" is worse than
   missing a few of the user's segments, because "what did I agree to" would
   then include other people's promises).
3. **Android**: an enrolment screen (record, play back, save, delete) and the
   same matching in the processing worker.
4. **Evaluation**: per meeting, per condition, per placement; confusion of
   `me` with each other speaker (who sounds like the user?).
5. **Privacy**: the voiceprint never leaves the device; deleting it removes
   all `is_me` labels' basis (labels are recomputed or marked stale).

## Open decisions

- **Enrolment sample.** Options: (a) one 30-second read paragraph — quick,
  read speech differs from conversation; (b) 2–3 minutes of natural speech
  from a past session, confirmed by the user — closer to real use, needs a
  session first; (c) (a) at setup, improved later with (b). Draft: (c).
- **Model hash mismatch.** If the speaker model changes, the voiceprint is
  invalid. Options: (a) force re-enrolment; (b) keep enrolment audio and
  recompute automatically (stores the user's voice sample); (c) ask the user.
  Draft: (c), with the sample kept only if the user agrees.

## You test this

1. Enrol on the phone. Then record a 5-minute session with one friend.
   Check the transcript: are your lines marked "me"?
2. Ask a friend with a similar voice to read the same paragraph; is it
   wrongly accepted as you?

## How this number could be lying

- Tuning meetings include the user's enrolment sample recorded the same day;
  held-out meetings (Step 17) are on other days with possibly different
  voice conditions (cold, tiredness).
- Accuracy by speech time is dominated by long turns; also report accuracy by
  segment count (short replies matter for "what did I agree to").

## Verification

- [ ] Enrolment, matching and deletion work on the laptop and both phones.
- [ ] "Me vs others" accuracy per condition and placement, by time and by
      segment, with intervals.
- [ ] Precision of `me` labels meets the Step 01 target (or the gap is
      reported).
- [ ] Voiceprint stays on the device (no network, no export).

## Files changed

- [NEW] `src/conversations/enrolment.py`
- [MODIFY] `src/memories/database.py` (`voiceprints` table)
- [NEW] `android/.../conversations/EnrolmentScreen.kt`
- [NEW] `docs/results/phase-5.1/step04-me.md`
- [MODIFY] `src/config.py`, `Taskfile.yml`, `README.md`

## Dependencies

- Step 03 (segments); Phase 3.1 Step 20 (speaker model).

## Common issues

- The phone on the table hears the user louder than others; loudness alone
  can look like a "me" detector. Check accuracy on the pocket / chest
  placement too.
