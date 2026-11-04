# Phase 4 Step 07b — Tier 0d: Hand-Activity Trigger (Optional Gate)

> NEW step, added 07 October 2026 from roadmap v2 §4 (Phase 4: "a
> hand-activity trigger as an optional extra gate"). Numbered 07b so existing
> step numbers stay unchanged.

## What

A gate that looks for **hands interacting with objects** and, when it sees
that, forces the frame through to Tier 1 / Tier 2 even if the cheaper gates
would have dropped it (a force-pass, like the IMU "settle" trigger in
Step 07). It uses the hand model chosen in Phase 3.1 Step 17 (for example
MediaPipe Hand Landmarker, if verified) at a low rate.

Signals, computed per frame on the downscaled image:

- `hand_present`: at least one hand detected above a score threshold,
- `hand_in_lower_centre`: the hand is in the part of the image where
  manipulation happens on a chest or head mount (region fixed per mount),
- `grasp_change`: the hand's shape changes between open and closed (distance
  between fingertip landmarks and palm) — a cheap proxy for pick-up and
  put-down,
- `hand_motion_stop`: the hand moved and then stopped (end of a reach).

Rule (to be tuned): force-pass when `grasp_change` or `hand_motion_stop`
happens while `hand_present`, with a short refractory period so one action
does not trigger ten frames.

## Why

- Step 08 already warns that small objects (keys) barely change a whole-frame
  embedding, so novelty can miss exactly the events users ask about.
  Tier 0a (pixel change) can miss them too when the hand covers the object.
  Hands are a strong cue that something is being picked up or put down.
- Probe B (Phase 3.1 Step 19) measures whether hand-centred perception can
  **identify** objects. This gate asks a simpler question: can hands tell us
  **when** to look? Even if Probe B's identification fails, this timing
  signal may still help the VLM path.
- It is optional by design. If it costs more than it adds, the ablation
  (B7 vs B5) removes it, which is a valid result.

## How to implement

1. **Reuse** `src/perception/hands.py` (Phase 3.1 Step 18); do not write a
   second hand wrapper.
2. **Gate function** in `src/vision/gates.py` (or a new
   `src/vision/hand_gate.py` if `gates.py` would pass 300 lines):
   `hand_gate(hands_now, hands_prev, state) -> (decision, reason, cost_us)`.
3. **Rate control**: run the hand model only on frames that Tier 0b did not
   reject as blurry, and at most at a configured rate (e.g. every second
   frame at 3 fps), because the hand model is more expensive than Tier 0a/0b.
   Cost per frame is logged.
4. **Refractory period** and thresholds in `src/config.py`
   (`MEMORY_HAND_GATE_*`).
5. **Decision log**: `tier0d: force|none, signal, value, us`, same format as
   other tiers, so the ablation tooling reads it.
6. **Evaluation**: on the tuning objects sessions, compare B5 and B7
   (B5 + Tier 0d): short-event recall (frame level and caption level, small
   objects separately), heavy calls per hour, cost per frame. Also on the
   EPIC-KITCHENS subset (exploratory, labelled).
7. **Golden fixtures**: hand landmarks for 20 frames + expected decisions,
   for the parity gate (Step 13).

## Open decisions

- **Signal used to trigger.** Options: (a) `hand_present` only — simplest,
  probably fires constantly while typing or cooking; (b) `grasp_change` —
  targets pick-up / put-down, sensitive to landmark noise; (c)
  `grasp_change` or `hand_motion_stop` (the draft) — catches more, two
  thresholds to tune.
- **Role in the cascade.** Options: (a) force-pass only (adds frames, never
  drops) — safe, may raise heavy calls per hour; (b) also suppress frames with
  no hands during "manipulation-heavy" scenes — saves calls, risks missing
  non-hand events (someone else moves your bag); (c) force-pass plus a
  "hand context" flag passed to Tier 2 so the VLM is asked about the hand
  region — more value per call, small prompt change.
- **Mount dependence.** Options: (a) one region rule for all mounts; (b) a
  region per mount (chest / head), stored in session meta; (c) no region rule
  (any hand anywhere). Chest and head mounts see hands in very different
  places.

## You test this

1. Laptop webcam debug page: sit still with hands off camera (expect no
   triggers), type on the keyboard (expect few or none), then pick up and put
   down your keys three times (expect a trigger each time). Tell me where it
   fired wrongly.
2. Watch the B5 vs B7 keyframe reels for the kitchen session side by side
   (blind). Which one shows more of the moments when you handled objects?

## How this number could be lying

- Hand landmarks are trained mostly on third-person, well-lit hands; an
  egocentric chest camera sees hands from above and at the image edge, so
  detection may be worse than the model card says. Hand detection rate on our
  frames is reported.
- Scripted sessions have deliberate, clear grasps; natural grasps are faster
  and partly hidden. Results are split by `scripted`.
- A recall gain bought with many more heavy calls is not a win on a phone.
  B7 is always shown on the calls-per-hour vs recall plot, not as recall
  alone.

## Verification

- [ ] Gate implemented reusing `src/perception/hands.py`; file under 300
      lines; settings in `src/config.py`.
- [ ] Decision log entries for every frame the hand model ran on.
- [ ] B5 vs B7 comparison on the tuning set: short-event recall (small objects
      separately), heavy calls per hour, cost per frame.
- [ ] Hand detection rate on our egocentric frames reported.
- [ ] Golden fixtures written for the parity gate.

## Files changed

- [NEW] `src/vision/hand_gate.py` (or [MODIFY] `src/vision/gates.py`)
- [MODIFY] `src/config.py`, `.env.example`
- [MODIFY] `src/benchmarks/keyframe_eval.py` (reads `tier0d` log entries)
- [NEW] `docs/results/phase-4/step07b-hand-gate.md`
- [MODIFY] `Taskfile.yml`, `README.md`

## Dependencies

- Phase 4 Steps 05–07 (the gates it sits next to); Phase 3.1 Steps 17–18
  (hand model and wrapper).

## Common issues

- Landmark jitter makes `grasp_change` fire on every frame: smooth landmark
  distances over 3 frames before thresholding.
- Gloves, sleeves and dark skin in dim light can lower detection rates;
  report detection rate per lighting condition and do not tune it away.
- Running the hand model on every frame on the Infinix may cost more than the
  whole Tier 0; measure at the parity gate before keeping it.
