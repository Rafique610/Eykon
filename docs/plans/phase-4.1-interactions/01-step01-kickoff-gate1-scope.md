# Phase 4.1 Step 01 — Kickoff: Gate 1 Scope Decision and Probe B Lessons

## What

Turn the Gate 1 outcome (Phase 3.1 Step 23) into a concrete scope for this
phase, and turn Probe B's failures into a list of things this phase must fix
or must accept:

1. Read the Probe B report, the Probe A report (for the VLM comparison
   baseline), the phone spot check and the decision note.
2. Choose the scope: **full**, **reduced** or **negative result**, using the
   rule written in the phase overview (viable / unclear / not viable).
3. Write `docs/results/phase-4.1/kickoff.md`:
   - scope chosen and why (quoting the Probe B numbers with intervals),
   - which steps are in and which are skipped,
   - the "lessons list": each Probe B failure type, its count, and which step
     addresses it (or "accepted limitation"),
   - the target numbers for Step 12, written now (see below),
   - the data this phase uses: tuning objects sessions, the EPIC subset, the
     held-out objects sessions (still locked).
4. Add a kickoff note to each in-scope step doc (one dated paragraph) if
   Probe B changed anything in it.

## Why

- This phase is "should" tier and conditional. Starting it without an
  explicit scope decision risks spending weeks on a path the evidence already
  said was weak, or dropping a path that was actually fine.
- Probe B was a prototype; its failure gallery is the most direct guide to
  what the real implementation must do differently. Writing the mapping down
  avoids re-learning the same lessons.
- Target numbers written **before** building (as in the Phase 3.1
  pre-registration) keep Step 12 honest.

## How to implement

1. Collect the headline Probe B numbers by script from
   `docs/results/phase-3.1/probe-b/*.csv` (no retyping).
2. Apply the scope rule from the phase overview. If the supervisor's Gate 1
   decision differs from the rule, follow the supervisor and record both.
3. Lessons list as a table: `failure type | Probe B count | cause | step that
   addresses it | expected effect`.
4. Target numbers for Step 12 (proposals for the user to confirm): for
   visible events, recall and precision for medium and large objects, and a
   separate, lower target for small objects; place accuracy target for
   put-downs. Tie each target to user impact (for example: "if recall for
   small objects is below X, 'where are my keys' is wrong more than one time
   in Y").
5. If scope is **negative result**: write a 1–2 page "why the cheap path did
   not work here" section with the evidence, then skip to Step 14 (which
   only writes up the comparison from existing Probe B data).

## Open decisions

- **Scope when Probe B is "unclear".** Options: (a) reduced scope as in the
  overview — builds the core, skips detector, tracker refinements and full
  integration; (b) full scope but with an early stop after Step 05 if
  identification accuracy does not improve over Probe B — more ambitious,
  needs a clear stop number; (c) postpone the phase until after Phase 5 —
  saves time now, risks never doing it.
- **Target numbers.** The user sets them in this step from the user-impact
  framing; the agent proposes values only from Probe B data, never invented.

## You test this

1. Read the lessons list. For each Probe B failure you watched in the
   gallery, does the "step that addresses it" make sense to you?
2. Confirm or change the target numbers. Say what "good enough" means to you
   as the user of the app.

## How this number could be lying

- Probe B ran on scripted sessions with a small vocabulary; scope decided on
  it may be optimistic. The kickoff note lists this caveat with the decision.
- Targets set close to Probe B results guarantee "success"; targets tied to
  user impact avoid that.

## Verification

- [ ] Scope decided and recorded with Probe B evidence and Gate 1 outcome.
- [ ] Lessons list with every Probe B failure type mapped to a step or
      accepted.
- [ ] Target numbers for Step 12 confirmed by the user.
- [ ] In-scope step docs annotated if Probe B changed them.

## Files changed

- [NEW] `docs/results/phase-4.1/kickoff.md`
- [MODIFY] in-scope step docs in `docs/plans/phase-4.1-interactions/`
  (kickoff notes)

## Dependencies

- Phase 3.1 Step 23 (Gate 1), Step 19 (Probe B report), Step 22 (phone spot
  check).

## Common issues

- Treating "unclear" as "viable" because the phase is interesting. The rule
  in the overview decides, unless the supervisor overrides.
