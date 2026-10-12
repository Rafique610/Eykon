# Phase 5.1 Step 16 — Noise and Overlapping-Speech Robustness Evaluation

## What

Measure, condition by condition, how noise, overlapping speech and phone
placement affect every stage, so the results can say **where** the pipeline
breaks:

| Condition (from the Phase 3.1 meeting matrix) | Sessions |
|---|---|
| clean, phone on table, polite turn-taking | 3 (target) |
| clean, overlapping speech segments | 2 |
| background noise (fixed level), phone on table | 2 |
| phone on body (pocket / chest) | 2 |
| AMI distant microphone (public) | subset |

Per condition: WER, DER, overlap DER, "me vs others" accuracy,
speaker-attributed WER, topic boundary F1, action item recall, summary
faithfulness counts (from Step 15), and per-category QA accuracy on the
conversation questions from these sessions.

Plus a **controlled noise test**: the same clean meeting re-run with recorded
café noise mixed in at 2–3 fixed levels (signal-to-noise ratios), to show how
each stage degrades as noise grows, with everything else unchanged.

## Why

- The handoff asks to "cover noisy audio and overlapping speech honestly".
  A single average number hides that the system may be fine in a quiet room
  and poor in a café.
- The controlled noise test isolates noise from other differences between
  sessions (different people, topics), which real sessions cannot do.
- These tables give practical advice for the app ("put the phone on the
  table"), which is a real user benefit, not only a research number.

## How to implement

1. `src/benchmarks/conversation_eval.py` (shared with Step 17): runs each
   stage's metric per session and groups by condition from the manifest.
2. Noise mixing with numpy at fixed signal-to-noise ratios (noise file from
   the Phase 3.1 protocol, consent-safe — no other people's speech).
3. Full pipeline re-run for the mixed versions (laptop; one level on the
   Pixel for a check).
4. Tables and a degradation plot (metric vs noise level) per stage.
5. Short "advice" section: which placement and conditions work, based only
   on these numbers.

## Open decisions

- **Noise levels.** Options: (a) 3 levels chosen by measured SNR of the real
  noisy sessions (so mixed audio matches reality); (b) fixed textbook levels;
  (c) (a) plus one harsher level. Draft: (a).
- **Speech enhancement (denoising) as a fix.** Options: (a) none — measure
  the baseline only; (b) test a small on-device denoiser before ASR — may
  help, adds a model and licence check; (c) only if noisy results miss the
  Step 01 targets by a lot. Draft: (c).

## You test this

1. Listen to the mixed noise versions of one meeting at each level. Which
   level sounds like a normal café to you?
2. Look at the degradation plot. At what noise level would you stop trusting
   the summaries?

## How this number could be lying

- Mixed noise is added to an already-recorded clean signal; real noisy rooms
  also make people speak louder and differently (Lombard effect). Real noisy
  sessions are reported next to the mixed ones.
- Two sessions per condition is small; per-session rows are shown, not only
  averages.

## Verification

- [ ] Every stage's metric reported per condition, with per-session rows.
- [ ] Controlled noise test at the chosen levels, with plots.
- [ ] One mixed level also run on the Pixel.
- [ ] Advice section written from the numbers only.

## Files changed

- [NEW] `src/benchmarks/conversation_eval.py`, `src/benchmarks/noise_mix.py`
- [NEW] `docs/results/phase-5.1/robustness.md`
- [MODIFY] `Taskfile.yml`, `README.md`

## Dependencies

- Steps 07–10, 15.

## Common issues

- Mixing noise into a WAV with clipping: normalise and check peak levels.
