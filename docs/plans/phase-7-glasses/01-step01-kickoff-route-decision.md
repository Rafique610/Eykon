# Phase 7 Step 01 — Kickoff: Route Decision and Scope

## What

1. **Survey** what capture hardware is realistically available: any
   programmable camera glasses within budget and allowed by their terms, a
   second Android phone for phone-as-glasses, head strap (from Phase 3.1).
   Record price, availability, programmability, and whether the device can run
   our models or only stream.
2. **Choose a route**: R1 real glasses, R2 phone-as-glasses, R3 analysis only
   (overview). Include the time box (stretch tier).
3. **Scope**: which splits (S0–S3) will be run end to end, which only
   modelled.
4. Write `docs/results/phase-7/kickoff.md`.

## Why

- Hardware availability decides everything in this phase; deciding early
  avoids building for a device we cannot get.
- Phase 6 results (Gate 4) show which components are cheap enough to move to a
  small device; they constrain the realistic splits.

## How to implement

1. Hardware table from manufacturer pages (verified, dated); no claims about
   specs that cannot be checked.
2. Route decision with the supervisor.
3. Time box and in-scope splits written down.

## Open decisions

- **Route** (R1 / R2 / R3).
- **Second phone for R2.** Options: (a) the Infinix as glasses and the Pixel as
  the phone — uses existing devices; the Infinix's low-end chip is a fair
  stand-in for a glasses chip; (b) borrow another phone; (c) the Pixel as
  glasses (unrealistically strong). Draft: (a).

## You test this

1. Wear the head strap with a phone for 15 minutes. Is it bearable for a
   one-hour experiment?

## How this number could be lying

- Glasses marketing specs (battery life, compute) are not measurements; they
  are used only in the projection (Step 08) and labelled.

## Verification

- [ ] Hardware survey table with sources and dates.
- [ ] Route, in-scope splits and time box recorded.

## Files changed

- [NEW] `docs/results/phase-7/kickoff.md`

## Dependencies

- Phase 6 Step 15.

## Common issues

- Consumer glasses that only stream through the maker's cloud app are not
  usable (zero-network rule); exclude them.
