# Phase 3.1 Step 05 — Recording Protocol and Capture Kit

## What

Write exact, repeatable instructions for every kind of recording session, so
that sessions recorded weeks apart, by different people, are comparable.
One protocol file per scenario pack, plus a shared checklist:

- `data/scenarios_v1/PROTOCOL.md` — shared rules (devices, settings, sync,
  naming, manifest fields, the before / during / after checklist). A copy
  without personal details is committed to `docs/results/phase-3.1/`.
- Pack A (objects and daily life): session types and **state-change
  scripts** (the planned object moves), plus rules for unscripted sessions.
- Pack B (meetings): meeting scenarios, roles, room setup, phone placement,
  noise conditions.
- Pack C (lecture / study group): setup for one main speaker plus slides or
  a whiteboard.
- Object vocabulary and place vocabulary per session (used by the slot
  schema, Step 02, and the taxonomy, Step 01).

This step also absorbs the protocol part of the old Phase 4 Step 01.

## Why

- Without a protocol, each session is recorded differently (different fps,
  different mount, phone in a pocket for half of it), and later
  differences in results are caused by recording differences, not by the
  system.
- **State-change scripts** produce ground truth almost for free: if the
  script says "11:02 keys desk → bag" and you say it out loud, annotation is
  quick and reliable.
- **Sync** between video, audio, IMU and the phone clock is the most common
  silent failure in multi-sensor data. A clap at the start and end of each
  session fixes it cheaply.
- Meetings need a controlled mix of easy and hard conditions (clean room vs
  café noise, polite turn-taking vs overlapping speech), otherwise Probe C
  only measures the easy case.

## How to implement

1. **Shared rules (`PROTOCOL.md`).**
   - Devices: Pixel 9 Pro XL (primary), Infinix Note 12 (for at least one
     session per pack, to see the low-end camera and microphone).
   - Video: 1080p, 30 fps, the phone's normal camera app **and** the Step 06
     capture app for sessions where IMU is needed. Never 4K (overheating,
     storage).
   - Audio: phone microphone, 16 kHz or higher, mono is fine; record what
     the phone really hears, no external microphone (it would hide real
     phone performance).
   - Sync: a loud clap visible on camera at the start and at the end; say the
     session id out loud after the first clap.
   - Naming: `<pack>_<YYYYMMDD>_<NN>`, e.g. `objects_20261012_01`.
   - Manifest fields filled right after recording: duration, device, mount,
     lighting (`bright` / `normal` / `dim`), location type, participants
     (codes only), consent ids, scripted (yes/no), notes, exclude ranges.
   - Checklist before: battery above 80 %, storage free, consent forms
     signed, airplane mode on (also proves no network use), Do Not Disturb.
   - Checklist after: copy to the raw directory, check file plays, fill
     manifest, write 3 lines of "what happened that the script did not plan".
2. **Pack A session types** (target at least 3 hours total, at least 6
   sessions, at least 40 % unscripted, from old Phase 4 Step 01):
   - desk work / study (long, static — tests over-sampling),
   - room tidying / kitchen (many short object interactions),
   - walking indoors and outdoors (motion, blur, IMU),
   - leaving the house routine (keys, wallet, charger, bag),
   - low-light evening session,
   - one conversation at home with a consenting family member or friend
     (feeds `conversation_recall`).
3. **State-change scripts.** At least 4 scripts, each 10–15 minutes, each
   moving 3–5 objects 2–4 times between named places, for example:
   keys: desk → bag → jacket pocket → key hook; wallet; charger; medicine
   box ("did I take my medicine"); passport mock-up. Each move is announced
   out loud ("keys into bag") to make annotation and audio alignment easy.
   One script is a "trap" script: an object is moved while partly hidden
   (behind a cup, inside a closed hand), because small hidden objects are the
   expected failure.
4. **Object and place vocabulary per session.** List the objects and the
   places that appear (e.g. `desk`, `bag`, `jacket_pocket`, `kitchen_counter`)
   with synonyms. Written before the session, extended after it if needed.
   Object size class (`small` / `medium` / `large`) per object, matching the
   taxonomy sub-tag.
5. **Pack B meetings** (target about 10 sessions of about 30 minutes,
   3–4 consenting people, planning default):
   - Scenarios with a real agenda so summaries and action items exist:
     project planning, choosing a group-trip plan, a study group dividing
     chapters, a mock client meeting. Each has 3–5 agenda points and at
     least 3 action items assigned to named participants.
   - Roles rotate so the user is not always the main speaker.
   - Conditions spread across sessions: clean quiet room; background noise
     (fan, café sound played from a speaker at a fixed volume); deliberate
     overlapping-speech segments (two people talking at once for a few
     seconds, at least 5 times per session in the "hard" sessions).
   - Phone placement: lying on the table in the middle (main), and in one or
     two sessions in the user's shirt pocket or on a chest clip (closer to
     the wearable case).
   - The user records a 30-second **voice enrolment** sample at the start of
     every session (feeds "me vs others" in Probe C and Phase 5.1).
   - Someone writes the real action items on paper at the end. That paper is
     a cheap extra ground truth for `action_items`.
6. **Pack C lecture / study group** (at least 1 session, 45–60 minutes):
   - One main speaker with slides or a whiteboard, 2–5 listeners asking a few
     questions.
   - Phone on the desk facing the board, plus audio. Note when slides change
     (or let the slide clicker be visible) for slide-change ground truth.
   - Only with the speaker's consent and the department's answer from Step 03.
7. **Mount** for Pack A (see open decision). A cheap chest clip or head strap.
   Note the mount in every manifest row.
8. **Pilot session.** Record one 10-minute Pack A script and one 10-minute
   two-person mini meeting. Go through the whole checklist and the Step 06
   capture app. Fix the protocol before the real sessions.

## Open decisions

- **Mount for Pack A.** Options: (a) chest clip — stable, misses what the
  eyes look at; (b) head strap — closest to future glasses, more blur;
  (c) both for one session to measure the difference (useful for the
  Phase 7 argument). From old Phase 4 Step 01, still open.
- **Noise level for "noisy" meetings.** Options: (a) a fixed recorded café
  track at a fixed volume measured with a phone sound meter app —
  repeatable; (b) a real café — realistic but other people's voices are
  recorded without consent (privacy rules forbid this); (c) a fan or
  air-conditioner only — repeatable, but not speech-like noise. (b) is ruled
  out by Step 03; choose between (a) and (c).
- **Scripted vs natural meetings.** Options: (a) fully scripted dialogue —
  perfect ground truth, unnatural speech; (b) agenda-only, natural talk —
  realistic, more annotation; (c) agenda-only plus a few planted facts
  ("the deadline moves to Friday") to guarantee testable questions. The
  draft leans towards (c).
- **Time cap.** See the phase overview: a fixed number of weeks, minimum
  quantities, or whichever comes first. To be fixed when the defense date is
  known.

## You test this

1. Do the pilot: one 10-minute Pack A script with the full checklist. How
   long did the checklist take? What did you forget?
2. Do the 10-minute mini meeting with one friend. Was the clap audible and
   visible? Did the voice enrolment get recorded?
3. Tell me which part of the protocol you would skip if you were tired.
   That part needs to become easier, not stricter.

## How this number could be lying

- Scripted sessions are easier than real life. At least 40 % of Pack A must
  be unscripted, and results are always split by `scripted`.
- Announcing moves out loud makes the audio path artificially strong for
  object questions. Results for object questions are reported both with
  and without the audio channel, or announcements are made quietly into a
  separate note-taking voice memo (see the annotation step).
- If only the user is ever the main speaker in meetings, "me vs others" looks
  better than it is. Roles rotate.

## Verification

- [ ] `PROTOCOL.md` with shared rules, three pack sections and checklists.
- [ ] At least 4 state-change scripts, including one trap script.
- [ ] Object and place vocabulary template, with size classes.
- [ ] At least 4 meeting scenario sheets with agenda and planted facts.
- [ ] Pilot Pack A session and pilot mini meeting recorded, problems listed,
      protocol updated.
- [ ] Manifest rows for both pilots validate with `task scenarios-validate`.

## Files changed

- [NEW] `data/scenarios_v1/PROTOCOL.md` (git-ignored, contains schedules) and
  `docs/results/phase-3.1/recording-protocol.md` (committed copy without
  personal details)
- [NEW] `docs/results/phase-3.1/scripts/` — state-change scripts and meeting
  scenario sheets
- [NEW] `src/scenarios/manifest.py` — manifest loader and validator
- [MODIFY] `Taskfile.yml` — `scenarios-validate`
- [MODIFY] `README.md`

## Dependencies

- Step 01 (categories decide what each session must produce).
- Step 03 (consent, privacy, storage).

## Common issues

- The phone stops recording when the screen locks or the camera app is
  backgrounded. Use the capture app from Step 06 or keep the screen on.
- Long recordings split into several files on some phones. The manifest
  allows a list of files per session with offsets.
- Overlapping speech that is planned sounds fake. Ask participants to really
  interrupt, but only on the agenda items marked for it.
