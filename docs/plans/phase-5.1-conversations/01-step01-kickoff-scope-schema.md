# Phase 5.1 Step 01 — Kickoff: Gate 1 Scope and Conversation Schema Check

## What

1. **Scope**: apply the overview's Probe C rule (usable / partly / unusable)
   to the Gate 1 outcome and write `docs/results/phase-5.1/kickoff.md`:
   chosen scope, the Probe C numbers it rests on (WER, DER, "me vs others"
   per condition), steps in and out, and target numbers for Step 17 written
   now.
2. **Schema check**: confirm that the conversation tables reserved in
   Phase 5 Step 01 (`sessions`, `speakers`, `utterances`, `topics`,
   `summaries`, `action_items`) exist and fit every conversation question
   category. Walk five real questions through them on paper.
3. **Data check**: list which recorded meetings, lecture sessions and AMI
   meetings are tuning, which are held-out (from `split_v1.json`), and how many
   questions per conversation category exist in `qa_v2.json`.

## Why

- Probe C decides how ambitious "who said what" can honestly be. Building full
  speaker naming when Probe C said speaker separation is unusable would waste
  weeks and produce misleading answers.
- Schema mismatches found late force migrations on real user data. Checking
  now, with real questions, is cheap.
- Targets written before building keep Step 17 honest (same practice as the
  Phase 3.1 pre-registration).

## How to implement

1. Pull Probe C numbers by script from `docs/results/phase-3.1/probe-c/`.
2. Apply the scope rule; note any supervisor override.
3. Schema walk-through table: `question | tables and columns used | missing?`
   for: "who suggested moving the deadline?", "what did I agree to do?",
   "summarise the meeting", "what did Sara say about the bus?", "what was on
   the slide about normalisation?". Missing columns are added as an additive
   migration (Phase 5 Step 01 rules: idempotent, backup, row counts).
4. Targets (user confirms): WER, DER and "me vs others" targets per
   condition; summary faithfulness target (for example: at most 1 unsupported
   bullet in 10); action item recall target; per-category QA targets. Each
   tied to user impact, never to published numbers from other datasets.

## Open decisions

- **Supervisor override.** If Gate 1 recommended a different scope than the
  rule, follow the supervisor and record the reasoning.
- **Targets**: set by the user here.

## You test this

1. For each of the five questions, point at the rows in the schema diagram
   that would answer it.
2. Confirm the targets as "what I would accept as a user".

## How this number could be lying

- Probe C used two own meetings plus AMI; the scope decision inherits that
  small sample. Step 16 re-measures across all conditions.

## Verification

- [ ] Scope chosen and recorded with Probe C evidence.
- [ ] Schema walk-through table complete; any additive migration applied and
      verified (row counts unchanged).
- [ ] Tuning / held-out meeting list and question counts per category.
- [ ] Targets confirmed by the user.

## Files changed

- [NEW] `docs/results/phase-5.1/kickoff.md`
- [MODIFY] `src/memories/database.py` (only if a column is missing)
- [MODIFY] `README.md`

## Dependencies

- Phase 3.1 Step 23 (Gate 1), Step 21 (Probe C). Phase 5 Step 01 (schema v2).

## Common issues

- Phase 5 Step 01 not finished yet: this step can define the conversation
  tables first; Phase 5 Step 01 then includes them unchanged.
