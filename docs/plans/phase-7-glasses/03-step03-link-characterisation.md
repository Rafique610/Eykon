# Phase 7 Step 03 — Link Characterisation: BLE and Wi-Fi Direct

## What

Measure the real links between our two phones (no internet involved):

- **BLE** (Bluetooth Low Energy, GATT with the largest negotiated packet
  size): throughput, latency, connection stability, energy per MB on the
  sending phone;
- **Wi-Fi Direct** (or a local hotspot without internet as a fallback):
  same measurements;
- at distances typical for glasses-to-pocket (under 1 m) and with the body in
  between (phone in a back pocket).

Output: a table of throughput (KB/s), latency (ms P50 / P90), energy (mJ per
KB) per link and condition, measured, with the measurement method.

## Why

- Link costs decide whether a split is feasible; published Bluetooth figures
  are theoretical maxima and do not include Android overheads.
- Energy per KB lets Step 08 trade radio energy against compute energy.

## How to implement

1. A small debug app mode with sender and receiver roles; fixed payloads;
   timing and battery current logged on both sides.
2. Repeated runs per condition; airplane mode with Bluetooth / Wi-Fi turned
   back on (no internet).
3. Results in `docs/results/phase-7/step03-links.md`.

## Open decisions

- **Links to test.** Options: (a) BLE only — closest to low-power glasses;
  (b) Wi-Fi Direct only — enough bandwidth for S0 / S1; (c) both (draft).

## You test this

1. Run the transfer test with the sender phone on your head strap and the
   receiver in your back pocket. Note any disconnections.

## How this number could be lying

- Phone radios are not glasses radios; the numbers describe our emulation and
  are projected separately (Step 08).
- Battery current on the Infinix may be coarse; repeats reduce noise.

## Verification

- [ ] Throughput, latency, energy per link and condition with repeats.
- [ ] Method documented.

## Files changed

- [NEW] `android/.../glasses/LinkBenchmark.kt`
- [NEW] `docs/results/phase-7/step03-links.md`
- [MODIFY] `AndroidManifest.xml` (Bluetooth / nearby Wi-Fi permissions)

## Dependencies

- Step 01.

## Common issues

- Android BLE packet size negotiation varies by phone; record the negotiated
  size.
