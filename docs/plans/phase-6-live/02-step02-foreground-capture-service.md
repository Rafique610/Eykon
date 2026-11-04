# Phase 6 Step 02 — Foreground Capture Service: Camera, Microphone, Sensors

## What

A single long-running Android foreground service that captures continuously:

- CameraX `ImageAnalysis` frames at the configured resolution and rate
  (Phase 3.1 Step 06 settings, adjusted by the scheduler later),
- microphone audio through VAD (speech segments only are kept, unless a
  conversation session is active, in which case the session recorder from
  Phase 5.1 Step 02 takes over),
- IMU at the configured rate,
- a persistent notification showing recording state with Pause and Stop,
  and a status screen in the app (recording time, frames processed, queue
  sizes, temperature),
- correct Android foreground service types (camera and microphone) and
  permission flow for the Android versions on both phones,
- watchdog: if the service is killed, it restarts (where Android allows) and
  records the gap.

## Why

- Live capture with the screen off is impossible without a correctly declared
  foreground service; Phase 3.1 Step 06 and Phase 4 Step 03 deliberately
  postponed this ("fine for the spike; Phase 6 adds the FGS").
- Visible recording state is both a legal / ethical requirement and the base
  for the privacy controls in Step 07.
- Measuring gaps from the start tells us how often Android interferes, which is
  itself a finding for the thesis.

## How to implement

1. `CaptureService` (Kotlin) with `ServiceInfo` types for camera and
   microphone; started from a "Start memory" button; stopped by the user or by
   the governor (Step 05) in critical states.
2. Reuse `SensorRecorder` and `AudioRecorder` from Phase 3.1 Step 06; frames
   go to the Phase 4 Kotlin cascade (Step 03 wires it), not to disk.
3. Lifecycle: survives screen off; handles camera taken by another app (pause
   and resume); handles phone calls (pause audio).
4. Gap logging: every interruption (start, end, reason) into telemetry.
5. Battery optimisation: detect whether the app is exempt; guide the user to
   exempt it; record the state.
6. Permissions: camera, microphone, notifications, activity recognition if
   needed for IMU on some versions; denial handled with a clear message.

## Open decisions

- **Camera during audio-only periods.** Options: (a) camera always on while
  recording memory — simplest, most power; (b) camera paused when the phone
  is dark (pocket) for N seconds — saves power (draft); (c) user-selectable
  "audio only" mode.
- **Audio retention outside sessions.** Options: (a) keep only transcripts
  of speech segments (draft) — private and small; (b) keep short audio
  segments for N days — allows replay, more storage; (c) user setting.

## You test this

1. Start memory, lock the phone, carry it for 30 minutes. Open the status
   screen: any gaps? How many frames processed?
2. Receive a phone call during recording. Does audio pause and resume?
3. Open the camera app while recording; then return. What happens?

## How this number could be lying

- Gaps depend on the phone maker's battery rules; Pixel and Infinix behave
  differently. Report per phone.
- A 30-minute test does not show overnight or full-day behaviour; Step 13
  does.

## Verification

- [ ] Service runs with the screen off for 30 minutes on both phones with
      gaps logged.
- [ ] Notification with Pause / Stop works.
- [ ] Interruptions (call, camera in use) handled and logged.
- [ ] Permissions and battery-optimisation state handled.

## Files changed

- [NEW] `android/.../live/CaptureService.kt`, `LiveStatusScreen.kt`,
  `CaptureWatchdog.kt`
- [MODIFY] `AndroidManifest.xml` (service, types, permissions)
- [MODIFY] `README.md`

## Dependencies

- Step 01; Phase 3.1 Step 06 (recorders); Phase 4 Step 13 (Kotlin cascade).

## Common issues

- Android versions differ in foreground-service rules; test on both phones'
  actual versions and record them.
- CameraX analysis keeps the camera hardware busy; release it promptly on
  pause to avoid blocking other apps.
