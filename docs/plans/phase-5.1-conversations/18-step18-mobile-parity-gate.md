# Phase 5.1 Step 18 — Mobile Parity Gate 5.1 (Conversation Pipeline on Pixel + Infinix)

## What

Prove the conversation pipeline produces the same results on both phones as
on the laptop, at a measured cost (roadmap v2: "phone parity for the
after-session processing"):

1. **Golden session**: one 10-minute meeting excerpt with laptop outputs
   frozen as references (ASR text, RTTM, utterances, topics, summary bullets
   at L0, action items at L0; L2 outputs compared loosely).
2. **Agreement on each phone**: WER between phone and laptop transcripts,
   DER between phone and laptop diarization, identical L0 summary bullets and
   action items given identical inputs (the rule-based parts must match
   exactly), L2 outputs compared by the support check and a human look.
3. **Full 30-minute sessions** processed on both phones (Step 11 chain):
   time per stage, battery used, peak temperature, thermal status, peak
   memory; on charger and on battery.
4. **Live recording check**: a 30-minute recording with the screen off on
   both phones completes without gaps.
5. **Measured slowdown factors** per stage added to the domain index.

## Why

- Roadmap §4: every phase ends with a phone exam. Conversation processing is
  the heaviest workload in the project (30 minutes of ASR plus a 2B model for
  summaries); the Infinix may struggle, and that must be known and handled
  (low-end mode), not hidden.
- Rule-based (L0) parts are deterministic; if they differ between laptop and
  phone, there is a port bug, which this gate catches.

## How to implement

1. Push the golden session audio and reference outputs to both phones
   (`task push-golden-session`).
2. Instrumented test runs the chain on the golden session and writes
   `parity_report.json`.
3. Full-session runs on both phones with telemetry from Step 11.
4. Compare with laptop numbers; explain every difference above the
   tolerances (decided below).
5. Low-end mode decision (Step 11 open decision) from the Infinix numbers.
6. Phase 2 fold-in: confirm that the original Phase 2 voice capture and Ask
   screen still work with the conversation features installed.

## Open decisions

- **Tolerances.** Options: (a) WER between phone and laptop at most 2
  percentage points, DER at most 3 points, L0 outputs identical; (b) looser
  for the Infinix if it uses a smaller ASR model (then compared with its own
  laptop run of the same small model); (c) set from laptop run-to-run
  variation. Draft: (a), with (b) for low-end mode.

## You test this

1. Record a real 30-minute meeting (consented) on the Pixel with the screen
   off, then let it process on the charger. Read the summary and ask 5
   questions.
2. Process the golden session on the Infinix and compare its summary with the
   Pixel's.

## How this number could be lying

- One golden session tests one set of voices; the full-session runs add more,
  but still our own meetings.
- Battery numbers depend on the charger and the starting temperature; both
  recorded.

## Verification

- [ ] Golden session agreement within tolerances on both phones (or every
      difference explained).
- [ ] Full 30-minute session processed on both phones with per-stage time,
      battery, thermal, memory.
- [ ] 30-minute screen-off recording without gaps on both phones.
- [ ] Slowdown factors in `docs/domain/eykon/index.md`.
- [ ] Low-end mode decided with numbers.

## Files changed

- [NEW] `android/.../conversations/` instrumented tests
- [NEW] `docs/results/phase-5.1/parity-report.md`
- [MODIFY] `docs/domain/eykon/index.md`, `Taskfile.yml`, `README.md`

## Dependencies

- Step 11 (processing chain), Step 17 (frozen config).

## Common issues

- Float differences in embeddings change clustering at the threshold edge;
  compare cluster assignments, not raw distances, and report borderline
  windows.
