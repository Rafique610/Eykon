# Phase 6 Step 06 — Battery-Aware and Low-End Modes

## What

Operating modes driven by **battery** and by **device class**, working
together with the thermal governor:

- **Battery modes**: above a high level → normal; middle → reduced
  perception rate, no VLM refinement; low → audio VAD and cheap perception at
  minimum rate; very low → capture stops with a saved state and a
  notification. Charging → after-session and consolidation jobs allowed.
- **Low-end profile** (Infinix): a fixed profile chosen from earlier parity
  gates (smaller ASR model if Phase 5.1 chose it, path C only, lower frame
  rate, generative answers on demand only, smaller evidence budgets).
- **User-facing choice**: "All-day" (battery saver) / "Balanced" /
  "Best memory" presets mapping to these settings, with the measured cost of
  each shown honestly (e.g. "about X % battery per hour on this phone", from
  this step's measurements).

Experiment: 2-hour live runs per preset on both phones, measuring battery per
hour, events captured per hour (vs the "Best memory" preset), answer latency.

## Why

- A memory assistant that empties the battery by lunchtime will not be used.
  Battery per hour vs memory quality is the trade-off users actually feel.
- The Infinix cannot run what the Pixel runs; an explicit low-end profile is
  honest and testable, unlike "it works, just slower".
- Presets with measured costs turn research numbers into a product decision
  the user can understand.

## How to implement

1. Battery levels from `BatteryManager`; modes in settings with hysteresis;
   combined with the thermal mode (the more restrictive wins).
2. Device profile chosen at first start from the device model or from a short
   benchmark (measured speed of the encoder and ASR), stored, overridable.
3. Presets screen; each preset's numbers filled from this step's measurements
   per phone (real data only — empty until measured).
4. 2-hour runs per preset per phone (same route / routine each time as far as
   possible; a replayed session for a controlled comparison too).

## Open decisions

- **Profile selection.** Options: (a) by device model list — simple, fails
  on unknown phones; (b) by a 30-second benchmark at first start — adapts,
  costs a little time; (c) (b) with a manual override (draft).
- **Default preset.** Options: (a) Balanced; (b) All-day; (c) decided after
  the field study from user feedback.

## You test this

1. On the Infinix, use "All-day" for 2 hours of normal activity. How much
   battery was used? Did it still remember the keys?
2. Switch presets and confirm the status screen shows the change.

## How this number could be lying

- Two-hour runs on different days differ in activity; the replayed-session
  comparison controls for that.
- Battery per hour drops as batteries age; record battery health if
  available.

## Verification

- [ ] Battery modes and device profiles implemented, combined with the
      thermal governor.
- [ ] Presets with measured numbers per phone.
- [ ] 2-hour runs per preset per phone with battery, events and latency.

## Files changed

- [NEW] `android/.../live/BatteryModes.kt`, `DeviceProfile.kt`,
  `PresetsScreen.kt`
- [NEW] `docs/results/phase-6/step06-battery.md`
- [MODIFY] `README.md`

## Dependencies

- Step 05.

## Common issues

- Battery percentage is coarse over short runs; use integrated current where
  reliable.
