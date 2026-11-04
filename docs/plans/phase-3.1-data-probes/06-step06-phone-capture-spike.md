# Phase 3.1 Step 06 — Phone Capture Spike: Video + IMU + Audio

> This step **executes `docs/plans/phase-4-keyframes/03-step03-phone-sensor-spike.md`**
> earlier than planned, with one addition (synchronised audio). That doc stays
> the reference for the camera and IMU details; this doc lists only what is
> different or added. Phase 4 Step 03 is marked "done in Phase 3.1 Step 06"
> once this step is approved.

## What

A debug-only screen in the existing Android app that records, on one shared
clock:

- camera frames through CameraX `ImageAnalysis` at the resolution and frame
  rate the product will really use (from Phase 4 Step 03: target 640×480,
  about 3 fps, JPEG per frame with nanosecond timestamps),
- accelerometer and gyroscope at about 100 Hz (CSV),
- **audio** at 16 kHz mono (WAV) with its start timestamp on the same clock
  — new in this step,
- phone telemetry every second: battery %, current, battery temperature,
  thermal status.

Plus the laptop side: `task pull-session` copies the session over ADB into
`data/scenarios_v1/<pack>/<session>/phone/`, and a small loader
`src/scenarios/phone_session.py` reads it and plots motion, audio level and
thumbnails on one timeline.

## Why

- Probes and later phases must be researched on **the input the product will
  really get**, not on the phone's normal 1080p camera app output (roadmap
  §4.1 "Same input" rule). Phase 4 Step 03 explains why for video and IMU.
- **Audio is added because Phase 5.1 (meetings) and Probe C need it**, and
  because the old plan only discovered in Phase 5 Step 04 that the current
  voice input (`RecognizerIntent`, Phase 2 Step 05) may use an online
  recogniser. Recording raw audio ourselves through `AudioRecord` avoids
  that entirely and lets us check airplane-mode behaviour now.
- One clock for video, IMU and audio means a spoken "keys into bag" can be
  matched to the exact frames, which makes annotation in Step 10 much faster.
- Phone-only problems (permissions, the camera stopping when the screen
  locks, MediaTek sensor rate limits) show up now, not in Phase 6.

## How to implement

1. **Precondition: the Android data layer.** The app does not build in this
   repo copy because `com.eykon.memory.data` (`MemoryDatabase`, `MemoryDao`,
   `MemoryRecord`) is missing (git-ignore bug, Step 03). The user has this
   package locally (confirmed 07 October 2026): copy it back into
   `android/app/src/main/java/com/eykon/memory/data/` after the Step 03
   `.gitignore` fix, build once, and commit it.
2. **Camera and IMU**: exactly as Phase 4 Step 03 "How to implement".
3. **Audio (new)**:
   - `AudioRecord` with `VOICE_RECOGNITION` source (less processing than the
     default on many phones; record which source was used in `meta.json`),
     16 kHz, mono, 16-bit PCM, written to `audio.wav` in chunks.
   - Store the clock time of the first audio buffer
     (`SystemClock.elapsedRealtimeNanos()`) in `meta.json`; camera and
     sensor timestamps on Android use the same boot-time base on most
     devices — verify on both phones, do not assume (see Verification).
   - `RECORD_AUDIO` permission requested at runtime.
4. **Telemetry**: as Phase 4 Step 03, plus the thermal headroom value if the
   API level supports it (`PowerManager.getThermalHeadroom`), recorded as
   `null` otherwise.
5. **Session folder**: `frames/`, `imu.csv`, `audio.wav`, `telemetry.csv`,
   `meta.json` (device model, Android version, build type, achieved fps,
   achieved sensor rate, audio source, start times, airplane mode on/off as
   read from settings).
6. **Pull and load**: `task pull-session -- <session_id>` (ADB `pull`), then
   `src/scenarios/phone_session.py` loads the folder and writes a timeline
   plot (`timeline.png`): gyro magnitude, audio loudness, telemetry
   temperature, with frame thumbnails every 10 seconds.
7. **Replay**: this step only needs loading and plotting. The full
   wall-clock replay harness with CPU and RAM caps is Phase 4 Step 02; it
   reads the same folder format.
8. **Clap check**: a script finds the start clap in both audio (loudness
   peak) and video (largest frame difference near the start) and reports the
   offset. This is the sync test.

## Open decisions

- Inherited from Phase 4 Step 03, still open: **frame storage** (JPEG per
  frame / H.264 in parallel / both for the spike) and **where the code lives**
  (debug-only screen / separate module).
- **Audio format.** Options: (a) WAV (raw PCM) — simplest, large (about
  115 MB per hour at 16 kHz 16-bit); (b) compressed (AAC / Opus) — small,
  but adds encoding cost and a decode step on the laptop; (c) WAV for the
  spike, decision revisited in Phase 6 for all-day capture.
- **Audio source.** Options: (a) `VOICE_RECOGNITION` — less automatic gain
  and noise processing on many phones, closer to raw; (b) `MIC` — default,
  processing varies by manufacturer; (c) record a short test with both on
  each phone and choose by measured ASR quality in Probe C.

## You test this

1. Install the debug build on the Pixel. Turn on airplane mode. Start a
   10-minute session: clap, say the session id, walk around the room, sit at
   the desk 3 minutes talking to yourself, move your keys twice saying it out
   loud, clap at the end.
2. Run `task pull-session -- <id>` and open `timeline.png`. Do the walking
   parts show motion? Do your spoken words show as loud parts at the right
   times?
3. Play `audio.wav`. Does it sound like what you said?
4. Repeat a shorter 3-minute version on the Infinix.
5. Note how warm each phone got.

## How this number could be lying

- Debug builds with logging are slower than release builds; telemetry is an
  upper bound on capture cost (from Phase 4 Step 03).
- Writing every frame as JPEG costs power the real product will not spend.
- One 10-minute session per phone says nothing about a full day; Phase 6 does
  that.
- The clock check passing on the Pixel does not mean it passes on the
  Infinix (different chipset, MediaTek). Both are checked separately.

## Verification

- [ ] Android data layer recovered (or the user decided on the fallback).
- [ ] All Phase 4 Step 03 verification items pass (frame/IMU clock drift
      under 10 ms over 10 minutes, fps within 10 % of target, dropped frames
      counted, works on Pixel and Infinix).
- [ ] Audio start time recorded; clap offset between audio and video under
      100 ms on both phones (to be confirmed as the right tolerance in this
      step).
- [ ] Session recorded in airplane mode completes normally (no network
      needed for capture).
- [ ] `task pull-session` and `phone_session.py` produce `timeline.png`.
- [ ] Size of the 10-minute session measured and written into the Step 03
      storage budget.

## Files changed

- [NEW] `android/.../capture/SensorCaptureScreen.kt`, `SensorRecorder.kt`
  (from Phase 4 Step 03), `AudioRecorder.kt` (new)
- [NEW] `src/scenarios/phone_session.py`, `src/scenarios/clap_sync.py`
- [MODIFY] `AndroidManifest.xml` (CAMERA, RECORD_AUDIO), navigation for the
  debug screen
- [MODIFY] `Taskfile.yml` — `pull-session`
- [MODIFY] `README.md`
- [MODIFY] `docs/plans/phase-4-keyframes/03-step03-phone-sensor-spike.md` —
  annotation "done in Phase 3.1 Step 06" after approval

## Dependencies

- Step 05 (protocol: what a session must contain).
- Android data layer present (see How to implement, item 1).

## Common issues

- Camera and microphone both in use: some phones refuse to give camera
  frames to an app that is also recording audio in the background. Keep the
  screen on and the app in the foreground for the spike.
- `AudioRecord` returns silence if another app holds the microphone (for
  example a voice assistant). Check the loudness plot.
- ADB pull of thousands of small JPEGs is slow; zip on the phone or pull the
  folder once at the end.
