# Phase 7 Step 05 — Transport Prototype with Backpressure and Loss Handling

## What

A small, reliable message transport between glasses side and hub:

- message types per split: keyframe (JPEG + metadata), audio segment,
  embedding + crop, slot record, control (start, stop, mode, clock sync);
- framing with a header (type, sequence number, timestamp, length);
- **backpressure**: when the link is slow, the sender drops by priority
  (provisional frames first, slot records last), mirroring the Phase 4 bounded
  queue policy;
- **loss handling**: reconnect automatically; buffer on the glasses side up to
  a limit while disconnected; report gaps;
- the same protocol over BLE and Wi-Fi Direct where feasible (BLE may carry
  only S3).

## Why

- Real links drop and slow down (body in the way, interference). Without
  backpressure, a slow link makes the glasses run out of memory or the hub fall
  behind silently.
- Gap reporting keeps the "what was missed" honest, as everywhere else in the
  project.

## How to implement

1. `GlassesTransport` (Kotlin) with a simple length-prefixed binary framing;
   no new protocol library unless needed (Ponytail).
2. Priority queue on the sender; drop policy configurable.
3. Clock sync messages: round-trip based offset estimation every minute.
4. Tests: unplug / disable radio mid-run; walk away and back; measure recovery
   time and data lost.

## Open decisions

- **Buffer limit while disconnected.** Options: (a) small (seconds) — low
  memory, loses more; (b) large (minutes) — better coverage, more glasses
  storage; (c) slot records always buffered, frames limited (draft).

## You test this

1. During a 10-minute S1 run, walk 15 m away from the hub phone and come back.
   What did the hub get? What was reported missing?

## How this number could be lying

- Lab disconnection tests are short; long walks with intermittent links are
  harder; one 30-minute walking run is included.

## Verification

- [ ] All message types sent and parsed correctly.
- [ ] Backpressure drops by priority; drops logged.
- [ ] Reconnect and buffering work; recovery time and loss measured.

## Files changed

- [NEW] `android/.../glasses/GlassesTransport.kt`, protocol constants
- [NEW] `docs/results/phase-7/step05-transport.md`

## Dependencies

- Steps 03, 04.

## Common issues

- BLE write-without-response can silently drop packets; use sequence numbers
  to detect gaps.
