# Phase 4.1 Step 09 — Interaction State Machine v2 (Five States)

## What

The core logic of this phase: for each tracked object, a small state machine
that turns hands, tracks and places into meaningful interaction events.

States per object (from handoff §9):

| State | Meaning | Entered when |
|---|---|---|
| `at_rest(place)` | object is lying somewhere | put-down confirmed, or object seen on a surface (detector) |
| `appears_in_hand` | object just appeared in a hand | track confirmed in hand, grasp `closed` |
| `carried` | object held while the user moves | in hand for more than T seconds, or camera / IMU motion while held |
| `released` | object left the hand | hand opens or held-object track ends |
| `placed(place)` | release confirmed at a place | object seen below / near the hand after release, or surface match |
| `taken(from_place)` | object picked up from a known place | `appears_in_hand` when last state was `at_rest(place)` |

Events emitted on transitions: `pick_up` / `take` (with from-place),
`carry_start`, `put_down` / `place` (with to-place), each with time,
confidence and evidence frame ids.

## Why

- A state machine is transparent: every event can be explained from the
  decision log ("hand closed on keys at 10:02:14, released at 10:02:31 above
  bag"). That explainability matters to the panel and for debugging.
- It separates **perception noise** (Steps 04–08) from **logic**; each can be
  tested on its own.
- `released` vs `placed` distinguishes "the hand opened" from "we know where
  it went", which is exactly what lets answers say "last seen in hand at
  10:02, probably in the bag" instead of guessing.

## How to implement

1. **`src/perception/interactions.py` v2**: one `ObjectState` per tracked
   object id; `step(observations, t) -> list[InteractionEvent]`.
2. **Transition rules** with minimum durations (hysteresis) and timeouts,
   all in settings:
   - `appears_in_hand` needs the confirmed track and grasp `closed` for at
     least N frames;
   - `released` when grasp opens or the track ends; becomes `placed` if
     within T seconds the object is seen on a surface or the surface match
     after release is confident; otherwise stays `released` (place unknown);
   - `carried` when in hand and the camera moves (IMU from the Phase 3.1
     session data, or frame motion if no IMU).
3. **Bag rule** (from Step 08): if the place is a tracked container (bag,
   drawer), the event's to-place is the container; the container's own place
   is resolved by its own state machine.
4. **Decision log** entries for every transition with the evidence.
5. **Unit checks**: scripted toy sequences (hand closes, carries, opens over
   desk) with expected events, run by `task interactions-check` (Taskfile
   one-liner pattern).
6. **First evaluation** on the tuning sessions (event precision / recall),
   full evaluation in Step 12.

## Open decisions

- **When the place is unknown at release.** Options: (a) emit `released`
  with place `null` — honest, answer layer says "last seen in your hand";
  (b) guess the current room cluster — often right at room level, sometimes
  wrong; (c) emit `released` with `null`, and attach the room cluster as a
  low-confidence hint field. Draft: (c).
- **Use of announced speech.** Options: (a) never — pure vision path;
  (b) allow speech ("keys in bag") as an extra observation — much more
  accurate in our scripted data but unfair to compare and unrealistic for
  natural use; (c) only in a separately labelled "multimodal" variant
  evaluated in Phase 5. Draft: (a) here.
- **Multiple objects in one hand.** Options: (a) only the top object; (b) up
  to two objects if both are confident; (c) treat as `uncertain`. Draft: (a)
  with the case counted.

## You test this

1. Run the toy sequence check: `task interactions-check`. All expected events
   must appear.
2. Laptop webcam: pick up your keys from the desk, walk a few steps, put them
   in your bag. Read the decision log: does it tell the story correctly?
3. Do it once with the keys hidden inside your hand. What does the log say?

## How this number could be lying

- Rules tuned on scripted, announced moves fit them well; natural moves are
  faster and messier. Split results by `scripted` and `announced`.
- A conservative machine (high thresholds) shows high precision but misses
  many events; precision and recall are always reported together.

## Verification

- [ ] State machine under 300 lines; all thresholds in settings.
- [ ] Toy sequence checks pass.
- [ ] Every emitted event has evidence frames and a decision-log trail.
- [ ] First tuning-set precision / recall recorded.

## Files changed

- [MODIFY] `src/perception/interactions.py`, `src/perception/runner.py`
- [MODIFY] `src/config.py`, `Taskfile.yml` (`interactions-check`)
- [NEW] `docs/results/phase-4.1/step09-state-machine.md`
- [MODIFY] `README.md`

## Dependencies

- Step 07 (tracks), Step 08 (places), Step 04 (grasp state).

## Common issues

- Releases detected when the object only leaves the camera view while still
  held: require the hand to be visible and open, not just the object missing.
- Long carries across rooms: the to-place is resolved where the release
  happens, not where the pick-up happened.
