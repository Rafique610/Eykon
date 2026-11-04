# Phase 3.1 Step 10 — Annotation Pass: Objects, Events and State Changes

## What

Annotate all Pack A tuning sessions (Step 07) — not the held-out ones —
using the tool and guide from Step 09:

- `events`: coarse activity segments (e.g. `desk_work`, `cooking`,
  `walking`), each with start and end,
- `short_events`: every pick-up, put-down, take and place of a vocabulary
  object, with time, object, from-place, to-place and `visibility`
  (`visible` / `partly` / `not_visible`),
- `state_changes`: derived from short events plus anything else that changed
  state (e.g. `stove: off → on`, `light: on → off`),
- `speech_gist` for the home conversation session,
- `exclude` ranges.

Then measure **inter-annotator agreement** on at least one session annotated
twice (by a second person, or by the user again a week later — see the
phase overview's open decision on the second labeller).

The 10-minute Probe B keys recording is annotated **first**, so Probe B can
start.

## Why

- This is the ground truth for short-event recall and event-boundary F1
  (Phase 4), interaction precision and recall (Probe B, Phase 4.1), and
  state-change query accuracy (Phase 5). These are the project's main
  numbers.
- The `visibility` flag matters for honesty: if a move happened inside a bag
  out of the camera's view, no camera-based method can see it. Results are
  reported for visible moves and for all moves separately, so the system is
  not blamed for the impossible, and not credited for guessing.
- Agreement between annotators tells us how precise the ground truth is.
  If two humans disagree on event boundaries by 4 seconds, a ±2 s boundary
  F1 target (roadmap §7) is measuring noise, and the tolerance must be
  revisited (Step 01 open decision).

## How to implement

1. **Order**: Probe B keys recording → the other state-change scripts →
   unscripted sessions → home conversation.
2. **Per session**: run `task annotations-prefill -- <session>` (announced
   moves become drafts), then annotate in the tool, then
   `task annotations-validate -- <session>`.
3. **Short events**: time = the moment the hand releases (put down) or
   closes on (pick up) the object, as defined in the guide. Unannounced
   moves seen while watching are added too and marked `announced: false`.
   This count is reported: it measures how much a script misses.
4. **State changes**: generated automatically from short events
   (`keys.location: desk → bag`) by `src/scenarios/derive_states.py`, then
   reviewed; non-location states are added by hand.
5. **Agreement session**: choose one 15–20 minute session by fixed rule (the
   second state-change script) for double annotation. The second annotator
   uses only the guide, not the first annotation.
6. **Agreement metrics** in `src/scenarios/agreement.py`:
   - short events: match events of the same object and verb within a
     tolerance; report precision and recall of annotator B against A and the
     median time difference of matched events;
   - event boundaries: boundary F1 at ±1 s, ±2 s and ±5 s;
   - state changes: percentage of identical final states per object.
   Output: `docs/results/phase-3.1/agreement-objects.md`.
7. **Tracking**: annotation minutes per session in the status table.

## Open decisions

- Who the second annotator is: see the phase overview (friend or
  classmate / user a week later / supervisor spot check).
- **What to do if agreement is low.** Options: (a) refine the guide and
  re-annotate the disputed parts — costs time, best ground truth; (b) keep
  both annotations and report system results against each — honest, more
  complex tables; (c) widen tolerances to the measured human disagreement —
  simplest, but must be justified with the agreement numbers. Decided after
  seeing the agreement report, with the rule written before seeing it: if
  boundary F1 at ±2 s between humans is below 0.8, option (a) for one round,
  then (c).

## You test this

1. Annotate the Probe B keys recording. Then watch it again at normal speed
   and count moves you missed in the annotation.
2. After the agreement session, read the agreement report. For the three
   largest disagreements, watch the video and decide who was right, and
   whether the guide needs a new rule.
3. Look at the share of moves marked `not_visible`. Does it match your
   memory of the sessions?

## How this number could be lying

- Annotating your own scripted sessions, you remember what happened and
  "see" moves that the camera did not clearly show. The `visibility` flag
  plus the second annotator reduce this.
- Agreement measured on one scripted session is higher than on unscripted
  ones. If time allows, double-annotate a short unscripted segment too.
- Automatic state derivation copies annotation errors into state changes.
  The review pass is required, not optional.

## Verification

- [ ] All Pack A tuning sessions annotated and validated; held-out sessions
      untouched.
- [ ] Probe B keys recording annotated first, with visibility flags.
- [ ] State changes derived and reviewed.
- [ ] Agreement report with short-event precision / recall, median time
      difference, boundary F1 at three tolerances.
- [ ] Count of unannounced moves found during annotation reported.
- [ ] Annotation minutes per session recorded.

## Files changed

- [NEW] `data/scenarios_v1/objects/<session>/annotations.json` (git-ignored)
- [NEW] `src/scenarios/derive_states.py`, `src/scenarios/agreement.py`
- [NEW] `docs/results/phase-3.1/agreement-objects.md`
- [MODIFY] `docs/results/phase-3.1/data-status.md` (generated)
- [MODIFY] `Taskfile.yml` — `annotations-agreement`
- [MODIFY] `README.md`

## Dependencies

- Step 07 (recordings), Step 09 (tool, formats, guide, pre-fill).

## Common issues

- Fatigue: annotation quality drops after about an hour. Annotate in short
  blocks and note the block in the time sheet.
- Places that are not in the vocabulary appear (a chair you put the bag on).
  Add them to the session vocabulary with a note; never force a wrong place.
- Two objects moved at once (keys and wallet together into the bag): two
  short events with the same time.
