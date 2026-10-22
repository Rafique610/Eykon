# Phase 5.1 Step 02 — Session Lifecycle: Start / Stop, Recording Service, Storage

## What

The user-facing start of every conversation feature: a **session** with a
clear start and end.

- **Phone**: a "Start meeting" / "Start lecture" button that starts a
  foreground service recording 16 kHz mono audio (reusing the Phase 3.1
  Step 06 `AudioRecorder`), with an ongoing notification, a timer, and a
  "Stop" button. Optional title and expected number of speakers.
- **Laptop**: the same lifecycle for pre-recorded files — "import a meeting
  recording" creates a session from a WAV / video file with its original
  timestamps.
- **Storage**: a `sessions` row (id, kind, title, start, end, device,
  expected_speakers, status: `recording` / `recorded` / `processing` /
  `done` / `failed`), audio file in app-private storage, and status updates
  as later steps run.
- **Safety**: recording survives screen off; stops cleanly on low battery or
  storage; never uploads anything; visible indicator whenever recording.

## Why

- Roadmap v2: "session start and stop by button first; automatic detection of
  a meeting later". A button is reliable, easy to explain, and respects
  consent (everyone sees the phone is recording).
- Every later step (ASR, diarization, summaries) reads from a session. A
  clean session model with statuses makes after-session processing resumable
  and testable.
- Android requires a foreground service with a microphone type and a visible
  notification for background recording; getting this right early avoids
  silent recording failures later.

## How to implement

1. **Android**: `ConversationRecordingService` (foreground service type
   `microphone`), started from a new "Sessions" screen; writes WAV in chunks
   (crash-safe), updates the session row; notification with stop action.
   Permission flow for `RECORD_AUDIO` and `POST_NOTIFICATIONS`.
2. **Laptop**: `src/conversations/sessions.py` — `create_session()`,
   `import_recording(path, kind, title)`, `set_status()`, `list_sessions()`;
   plain `sqlite3`, parameterised.
3. **Session folder layout** (both sides): `audio.wav`, `meta.json` (device,
   audio source, start clock), later `asr.json`, `diarization.rttm`, etc.
4. **Limits**: maximum session length setting (e.g. 2 hours); low storage
   warning; battery under a threshold stops recording with a saved partial
   session.
5. **Consent reminder**: a one-line reminder on the start screen ("make sure
   everyone agrees to be recorded"), dismissible; consistent with Phase 3.1
   privacy rules.
6. **Airplane mode**: the whole flow works with no network.

## Open decisions

- **Automatic meeting detection.** Options: (a) not in this phase — button
  only (roadmap v2 default); (b) suggest a session when sustained
  multi-speaker speech is detected — convenient, privacy questions;
  (c) later in Phase 6 as an experiment. Draft: (a) now, (c) later.
- **Audio format for long sessions.** Options: (a) WAV (about 115 MB per hour
  at 16 kHz 16-bit) — simple, no decode cost; (b) compressed (Opus / AAC) —
  about a tenth of the size, encoding cost; (c) WAV while processing, then
  compress or delete after processing per retention setting. Draft: (c).

## You test this

1. Start a session on the phone, lock the screen, talk for 3 minutes, stop.
   Does the session appear with the right length? Play the audio.
2. Start a session, then switch to airplane mode and back; nothing should
   change.
3. On the laptop, import one recorded meeting from Phase 3.1 and check its
   session row and folder.

## How this number could be lying

- Short test sessions hide long-session problems (file size, battery,
  Android killing the service). Step 18 and Phase 6 test 30-minute and longer
  sessions.

## Verification

- [ ] Recording continues with the screen off for at least 30 minutes on both
      phones (measured in Step 18; smoke-tested here for 5 minutes).
- [ ] Session statuses update correctly; a crash during recording leaves a
      playable partial file and a `failed` or `recorded` status.
- [ ] Laptop import works for all Phase 3.1 meetings.
- [ ] No network permission used by the recording flow.

## Files changed

- [NEW] `android/.../conversations/ConversationRecordingService.kt`,
  `SessionsScreen.kt`, `SessionRepository.kt`
- [MODIFY] `AndroidManifest.xml` (service, permissions)
- [NEW] `src/conversations/__init__.py`, `src/conversations/sessions.py`
- [MODIFY] `Taskfile.yml` (`session-import`), `README.md`

## Dependencies

- Step 01; Phase 3.1 Step 06 (`AudioRecorder`); Phase 5 Step 01 (tables).

## Common issues

- Some phones stop foreground services under battery optimisation; ask the
  user to exempt the app and record whether they did.
- Another app holding the microphone (call, voice assistant) gives silence;
  detect a silent first minute and warn.
