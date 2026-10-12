# Phase 6.5 Step 06 — Cross-Session Voice Names (Consented)

## What

Build on Phase 5.1 Step 06 (per-session speaker naming): when the user names
a speaker **and** records that person's consent, keep a voiceprint for them so
future sessions label that voice automatically:

- `people_voiceprints` (person id, embedding, sample count, model hash,
  created_at), encrypted like face descriptors;
- in new sessions, speaker clusters are compared with known voiceprints;
  matches above a threshold get the name (shown as "probably Sara" when
  confidence is medium);
- voiceprints update with confirmed new sessions;
- "forget this voice" deletes the voiceprint and names in future sessions
  (past sessions keep "speaker N" unless the user re-names them).

## Why

- Voice naming is lower risk and more reliable in meetings than faces (the
  phone often does not see faces at all when lying on a table).
- It is the "voices only" scope option at Step 02 and can ship without faces.

## How to implement

1. `src/people/voices.py`, Kotlin mirror; reuse `src/speech/speakers.py`
   embeddings.
2. Threshold tuned on consented sessions not used for evaluation.
3. Evaluation: across held-out consented meetings, share of speaking time
   with the correct name, false names (wrong person named), "probably" rate.

## Open decisions

- **Threshold policy.** Options: (a) strict — few wrong names, more "speaker
  N"; (b) loose — more names, more mistakes; (c) strict for automatic names,
  loose for "probably" suggestions (draft).

## You test this

1. Name a friend in one meeting; record a second meeting with them a few days
   later. Are they named automatically?
2. Have a different person with a similar voice speak; are they wrongly named?

## How this number could be lying

- Recurring participants in all meetings make cross-session naming look
  easy; include at least one meeting with a new person.

## Verification

- [ ] Voiceprints stored only with consent; encrypted.
- [ ] Automatic naming in new sessions with confidence wording.
- [ ] Correct-name share, false names measured on held-out consented meetings.
- [ ] "Forget this voice" works.

## Files changed

- [NEW] `src/people/voices.py`, `android/.../people/VoiceNames.kt`
- [MODIFY] Phase 5.1 naming screen (consent and "remember" toggle), `README.md`

## Dependencies

- Step 02; Phase 5.1 Steps 05–06.

## Common issues

- Speaker model updates invalidate voiceprints (model hash); ask the user to
  re-confirm rather than silently matching with a different model.
