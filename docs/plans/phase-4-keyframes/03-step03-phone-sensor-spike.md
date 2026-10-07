# Step 03 — Phone Sensor-Capture Spike (Video + IMU, Real Pipeline)

## What
A minimal Android screen/service in the existing app that records what the
real product will see: CameraX `ImageAnalysis` frames at the target resolution
and fps, plus accelerometer + gyroscope at ~100 Hz, all on one monotonic
clock. Output: a session folder pulled via ADB and replayable on the laptop.

## Why
- The laptop has no IMU; Tier 0c can only be researched with real traces.
- CameraX output (resolution, YUV, auto-exposure, frame drops) differs from a
  phone's normal video recording. Researching on the wrong input is how laptop
  results fail on mobile.
- Early phone spike = we learn about phone-only problems now, not in Phase 6.

## How to implement
- CameraX `ImageAnalysis` with `STRATEGY_KEEP_ONLY_LATEST`, target 640×480,
  sample every Nth frame to 3 fps; save JPEG (quality 90) + timestamp
  (`image.imageInfo.timestamp`, nanoseconds, same base as
  `SensorEvent.timestamp`).
- `SensorManager` listeners for `TYPE_GYROSCOPE` and `TYPE_ACCELEROMETER` at
  `SENSOR_DELAY_GAME`; write CSV.
- Also record phone telemetry each second: battery %, current (µA), battery
  temp, thermal status (`PowerManager.getCurrentThermalStatus`).
- Session folder: `frames/`, `imu.csv`, `telemetry.csv`, `meta.json`.
- `task pull-session` (ADB) → `data/ego_v1/<session>/phone/`.

## Open decisions
- **Frame storage on phone**: (a) JPEG per frame — simple, replayable;
  (b) H.264 via `MediaRecorder` in parallel — smaller, but timestamps harder to
  align with analysis frames; (c) both for the spike only.
- **Where the code lives**: (a) debug-only screen in the existing app — fastest;
  (b) separate module — cleaner but more Gradle work. (a) recommended for a spike.

## You test this
1. Install the debug build, start a 10-min session, walk around your room,
   sit at the desk 3 min, then walk downstairs.
2. Pull the session and open the auto-generated plot (gyro magnitude over time
   with thumbnails) — do the motion spikes line up with what you remember?
3. Note how warm the phone got and the battery % drop (written to telemetry,
   but your hand-feel matters too).

## How this number could be lying
- A debug build with logging on is slower than release → note build type.
- Saving JPEGs costs power that the real product won't spend → telemetry from
  the spike is an *upper bound* for capture cost.

## Verification
- [ ] Frame timestamps and IMU timestamps on the same clock (drift < 10 ms over 10 min).
- [ ] Achieved fps within 10 % of target; dropped frames counted.
- [ ] Session replays on the laptop through `src/vision/replay.py`.
- [ ] Works on Pixel **and** Infinix.

## Files changed
- [NEW] `android/.../capture/SensorCaptureScreen.kt`, `SensorRecorder.kt`
- [MODIFY] `AndroidManifest.xml` (CAMERA permission), `Taskfile.yml`, `README.md`

## Dependencies
- Step 02 (replay harness for the laptop side).

## Common issues
- Camera stops when screen turns off without a foreground service — fine for
  the spike; Phase 6 adds the FGS.
- Some MediaTek devices clamp sensor rate — record actual rate in `meta.json`.
