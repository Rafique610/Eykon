# Phase 4.1 Step 10 — State-Change Records and the Ledger Interface

## What

Turn interaction events into the records Phase 5's entity-state table
consumes, and fix the interface between the two phases:

1. **State-change record fields** (handoff §9), carried inside a slot record
   (`kind: interaction`, `producer.path: cheap`):
   - `entity` — the object id from the user's list (normalised name),
   - `attribute` — `location` (also `holder: user` while carried),
   - `new_value` — place label / surface / container, or `null` if unknown,
   - `old_value` — previous place if known,
   - `t` — event time,
   - `confidence` — calibrated (Step 05 calibration combined with state
     machine rules),
   - `evidence_frames` — frame ids or thumbnail paths,
   - `hint` — e.g. the room cluster when the surface is unknown.
2. **Interface contract** `docs/results/phase-4.1/ledger-interface.md`: what
   the ledger can assume (one record per transition, times monotonic per
   entity, confidence meaning), and what it must handle (late corrections,
   `null` places, conflicting records from the VLM path).
3. **Writer**: records are written to the memory store through the same
   function Phase 5 Step 03 uses for provisional events (until then, to
   `MemoryRecord.metadata["slot"]`, as in Phase 3.1 Step 02).
4. **Golden fixtures**: 10 interaction slot records with expected ledger
   states after applying them in order.

## Why

- Phase 5 Step 07 (entity-state ledger) is the project's main research
  contribution for memory (P2). Its quality depends on clean, well-defined
  inputs. Agreeing the contract now avoids each phase assuming something
  different.
- Two producers (cheap path and VLM path) will write location changes for the
  same object. The contract defines how conflicts are represented so the
  ledger can resolve them explicitly instead of by accident.

## How to implement

1. Extend `src/memories/slots.py` validation for `kind: interaction` with the
   fields above (schema version stays `slot-v1` if fields are additive; if
   not, bump to `slot-v1.1` with a changelog).
2. `src/perception/records.py`: `event_to_slot(event) -> SlotRecord`.
3. Contract document with examples: normal move, unknown place, carried
   across rooms, object put into a tracked bag, conflicting VLM record.
4. Golden fixtures in `data/golden/interactions/` (copy in
   `docs/results/phase-4.1/golden-interactions/` for Kotlin).
5. A small replay function `apply_in_order(records) -> dict[entity, state]`
   used only for testing the contract (the real ledger is Phase 5 Step 07).

## Open decisions

- **Who resolves conflicts between producers.** Options: (a) the ledger,
  using confidence and time (Phase 5 Step 07) — single place for logic;
  (b) Tier 2 picks one record before writing — simpler ledger, loses
  information; (c) both records stored, ledger marks `ambiguous` when they
  disagree — most honest, answers must handle ambiguity. Recommended for
  discussion with Phase 5 Step 07; this step only defines how both are
  represented.
- **Carry state in the ledger.** Options: (a) `holder: user` stored as a
  state — enables "I had them in my hand at 10:05"; (b) not stored, only
  location changes — smaller ledger; (c) stored but expired automatically
  after release.

## You test this

1. Read the contract examples. For "keys into bag, bag moved to car", does
   the expected ledger state answer "where are my keys?" the way you would?
2. Run `task interactions-golden-check` and confirm all 10 fixtures produce
   the expected states.

## How this number could be lying

- Golden fixtures are written by us and test only the cases we thought of.
  Step 12's real sessions test the rest.

## Verification

- [ ] Slot validation covers interaction fields; schema version handled.
- [ ] `records.py` under 300 lines.
- [ ] Contract document with at least 5 worked examples, agreed with the
      Phase 5 Step 07 plan (annotation added there).
- [ ] Golden fixtures pass.

## Files changed

- [MODIFY] `src/memories/slots.py`
- [NEW] `src/perception/records.py`
- [NEW] `docs/results/phase-4.1/ledger-interface.md`,
  `docs/results/phase-4.1/golden-interactions/`
- [MODIFY] `docs/plans/phase-5-memory/07-step07-entity-state-ledger.md`
  (annotation pointing to the contract)
- [MODIFY] `Taskfile.yml`, `README.md`

## Dependencies

- Step 09. Phase 3.1 Step 02 (slot schema).

## Common issues

- Times in seconds from session start vs wall-clock time: the record keeps
  both when available; the ledger orders by wall time for live data and by
  session time for recordings.
