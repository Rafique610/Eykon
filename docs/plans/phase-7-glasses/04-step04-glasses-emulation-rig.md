# Phase 7 Step 04 — Glasses Emulation Rig (Phone-as-Glasses)

## What

For route R2 (or R1 with real hardware): a "glasses mode" of the app that runs
on a head-worn device and does only the glasses-side work of a chosen split:

- capture (camera, microphone, IMU) as in Phase 6 Step 02,
- the stages assigned to the glasses for S1 / S2 / S3 (Tier 0, Tier 1,
  path C), reusing the same Kotlin code,
- a sender that hands outputs to the transport (Step 05),
- telemetry of its own compute, camera and radio energy.

The main phone runs a "hub mode" that receives and continues the pipeline.

## Why

- End-to-end split experiments need a real second device doing the
  glasses-side work with real costs; reusing the existing code keeps this
  cheap.
- The low-end Infinix as the glasses side approximates a weak glasses chip
  better than the Pixel would.

## How to implement

1. App modes: `glasses`, `hub`, `standalone` (default), selected in a debug
   screen.
2. Split selection setting decides which stages run on which side.
3. Head strap mount; capture settings identical to Phase 6.

## Open decisions

- **Display feedback on the glasses side.** Options: (a) none (screen off) —
  realistic for glasses; (b) minimal status LED / notification; (c) full app
  UI (unrealistic). Draft: (a).

## You test this

1. Wear the glasses-side phone, carry the hub phone, run 10 minutes in S1.
   Does the hub show events?

## How this number could be lying

- A phone on the head is heavier and has a bigger battery than glasses;
  battery life results are not glasses results (Step 08 projects).

## Verification

- [ ] Glasses and hub modes run each split's stage assignment.
- [ ] Telemetry on both sides.

## Files changed

- [NEW] `android/.../glasses/GlassesMode.kt`, `HubMode.kt`
- [MODIFY] `LivePipeline.kt` (stage placement by split)

## Dependencies

- Steps 01, 03; Phase 6 Steps 02–03.

## Common issues

- Clock differences between devices; timestamps synchronised at connection
  (offset measured) and checked with a clap.
