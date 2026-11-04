# Phase 3.1 Step 08 — Own Recordings: Mock Meetings and Lecture (Packs B and C)

## What

Record the conversation data for Probe C and Phase 5.1:

- **Pack B:** about 10 mock meetings of about 30 minutes each (minimum 8),
  3–4 consenting participants, using the meeting scenario sheets from
  Step 05 (agenda, planted facts, assigned action items), across the planned
  conditions: clean / noisy, polite / overlapping speech, phone on the table
  / phone on the user's body.
- **Pack C:** at least 1 lecture or study-group session of 45–60 minutes
  with slides or a whiteboard.
- For every session: the user's 30-second voice enrolment sample, the paper
  list of real action items written at the end, the consent ids, and the
  manifest row.
- At least 2 meetings are recorded as **held-out** (marked, not processed)
  for Phase 5.1's final evaluation.

## Why

- Meetings are the committed new scenario (roadmap v2, handoff §4). Phase 5.1
  needs real 30-minute conversations with ground truth; AMI (Step 04) is a
  useful second test set, but it is not recorded on a phone, not with our
  participants, and not in our rooms.
- Probe C must measure speaker separation and speech recognition on audio
  that looks like the real product input: a phone on a table or on the
  user's body, in an ordinary room.
- Planned conditions (noise, overlap, placement) turn "it works / it does
  not work" into a table showing **where** it breaks, which is what the
  panel and Gate 1 need.

## How to implement

1. **Schedule** sessions with the participants. Fill a condition matrix in
   `PROTOCOL.md` so the 10 meetings cover:

   | Condition | Sessions (target) |
   |---|---|
   | Clean room, phone on table, polite turn-taking | 3 |
   | Clean room, phone on table, overlapping speech segments | 2 |
   | Background noise (chosen in Step 05), phone on table | 2 |
   | Phone on user's body (pocket or chest clip) | 2 |
   | Held-out (any mix, recorded but not processed) | at least 2 of the above |

   The exact counts can shift; the matrix keeps each condition represented.
2. **Before each meeting**: consent forms checked (Step 03), scenario sheet
   handed out, phone in airplane mode, Step 06 capture app recording audio
   (plus normal video if participants agreed to video).
3. **During**: start clap and session id; user's voice enrolment (read a
   fixed paragraph, 30 seconds); meeting; end clap.
4. **After**: participants write the agreed action items on paper, signed
   by the person who owns each item; photo of the paper goes into the
   session folder. Fill manifest: participants (codes), condition, room,
   noise level as measured, placement, duration, held-out or tuning.
5. **Lecture**: same procedure; note slide changes (or keep the slide clicker
   visible); photograph the whiteboard at the end; get the slides file from
   the speaker if they agree, for OCR ground truth in Phase 5.1.
6. **Extraction**: `task scenarios-extract -- <session>` writes
   `audio_16k.wav` (and frames for the lecture) into
   `data/scenarios_v1/meetings/<session>/` or `.../lecture/<session>/`.
7. **Status**: `task scenarios-status` now also shows meeting hours per
   condition and the number of distinct speakers.

## Open decisions

- **Video in meetings.** Options: (a) audio only — easier consent, smaller
  files, enough for speech and speaker work; (b) audio plus video — enables
  later face work (Phase 6.5, stretch) and "who is speaking" from lips, but
  harder consent and privacy; (c) video only in the 2–3 sessions where all
  participants tick "video yes". The draft follows (c).
- **Same participants in every meeting or rotating.** Options: (a) same
  3–4 people — speaker enrolment can be reused, but results only reflect
  those voices; (b) rotating — harder for speaker separation, more realistic;
  (c) a fixed core of 3 with one rotating guest. Consent logistics decide
  this as much as research does.
- **Lecture source.** Options: (a) a real class with the lecturer's
  consent — realistic, needs department approval; (b) a classmate gives a
  mock lecture — fully controlled, less realistic; (c) a study-group session
  where one person explains a topic — middle ground.

## You test this

1. After the first meeting, listen to 1 minute from the start, middle and end
   of the phone recording. Can you understand everyone? Write down who was
   hard to hear and why (distance, voice, noise).
2. Compare the paper action items with what you remember. Anything missing?
3. After all sessions, look at `task scenarios-status` and confirm each
   condition in the matrix has at least one session.

## How this number could be lying

- Mock meetings with friends are friendlier and more structured than real
  meetings. Results are labelled "mock meetings" everywhere; AMI provides a
  second, independent check.
- If the same 3 people appear in every meeting, speaker separation may look
  good only for those voices. Reported per speaker and per participant set.
- Planted facts make some questions easier than natural ones. Questions are
  tagged `planted: true/false` in Step 12 and reported separately.

## Verification

- [ ] At least 8 meetings recorded (target 10), each about 30 minutes, with
      consent ids.
- [ ] Every condition in the matrix has at least one session.
- [ ] At least 2 meetings marked held-out and untouched.
- [ ] Every meeting has a voice enrolment sample and a photo of the paper
      action items.
- [ ] At least 1 lecture or study-group session with slide-change notes or
      the slides file.
- [ ] All sessions validate and have audio extracted.

## Files changed

- [MODIFY] `data/scenarios_v1/manifest.json` (git-ignored)
- [MODIFY] `src/scenarios/status.py` — meeting statistics
- [MODIFY] `docs/results/phase-3.1/data-status.md` (generated)
- [MODIFY] `README.md`

## Dependencies

- Step 03 (consent, ethics answer), Step 05 (scenario sheets, conditions),
  Step 06 (audio capture app; the normal phone voice recorder is the
  fallback if the app is not ready, noted in the manifest).

## Common issues

- Participants speak "for the recording" at first and naturally later.
  Start the agenda after a 2-minute warm-up and mark the warm-up as
  excluded or as a separate segment.
- Phone on the table picks up table taps and cups; ask people not to tap
  the table but do not forbid normal behaviour.
- A participant leaves halfway. Note the time in the manifest; speaker
  counts change.
