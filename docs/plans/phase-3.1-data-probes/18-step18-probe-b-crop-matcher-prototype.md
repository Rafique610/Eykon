# Phase 3.1 Step 18 — Probe B Prototype: Hand-Centred Crop Matcher

## What

A small, LLM-free prototype in a new feature folder `src/perception/` that,
for each frame of a session:

1. finds hands (hand model from Step 17),
2. cuts a crop around each hand (box around the landmarks, enlarged by a
   fixed factor),
3. embeds the crop with the image-text model and compares it with text
   embeddings of the session's object vocabulary ("a photo of keys in a
   hand", …), giving a score per object,
4. decides per frame whether a vocabulary object is **in hand**, and which,
5. turns the per-frame in-hand sequence into **events**: `pick_up` when an
   object appears in hand and stays for a minimum time; `put_down` when it
   disappears from the hand while the hand is near a surface (or simply
   disappears, in the simplest version),
6. writes every event as a slot record (`kind: interaction`,
   `producer.path: cheap`) with confidence and cost.

Also a place guess for put-down: the image embedding of the full frame at
put-down time compared with text embeddings of the session's place
vocabulary ("a desk", "an open bag"…). Simple, and explicitly a prototype —
Phase 4.1 does place recognition properly.

## Why

- This is the "cheap perception" side of Probe B and the first concrete
  answer to the supervisor's "can it be done with embeddings, detection and
  tracking instead of an LLM?"
- Most objects people lose are things they handled. Looking only where the
  hand is, instead of describing the whole scene, is far cheaper and focuses
  on the moments that matter.
- Writing slot records means Step 19 scores this path and the VLM path with
  the same code.

## How to implement

1. **Files** (each under 300 lines):
   - `src/perception/hands.py` — load hand model, `detect_hands(frame) ->
     list[Hand]` (landmarks, box, handedness, score).
   - `src/perception/crop_match.py` — `crop_around(hand, frame)`,
     `match_crop(crop, vocab_embeddings) -> list[(object, score)]`, text
     embeddings cached per vocabulary.
   - `src/perception/interactions.py` — the per-frame to event logic as a
     small state machine with three states per hand: `empty`,
     `holding(object)`, `uncertain`; transitions need a score above a
     threshold for a minimum number of consecutive frames (hysteresis, so
     one noisy frame does not create an event).
   - `src/perception/runner.py` — run over a session's frames and write
     slot records to `data/probes/b/cheap/<session>.jsonl`.
2. **Frame rate**: process at the same rate the phone pipeline delivers
   (Step 06, about 3 fps), from the 640×480 frames.
3. **Thresholds**: score threshold, minimum frames for pick-up and put-down,
   crop enlargement factor. Tuned **only** on one designated tuning script
   session (not the keys recording and not any session used in Step 19's
   scoring), by a small grid, and then frozen before Step 19. The tuning
   session is named in the pre-registration.
4. **Cost**: per frame latency for each stage (hands, crop, embedding,
   logic) and peak memory, laptop CPU, emulation profile.
5. **Debug view**: `task perception-debug -- <session>` writes a short
   video or contact sheet with hand boxes, top-3 object scores and event
   markers, so failures can be seen.
6. **Settings** for thresholds go in `src/config.py` (`MEMORY_PERCEPTION_*`),
   not as constants scattered in code.

## Open decisions

- **Put-down detection.** Options: (a) object simply disappears from hand —
  simplest, false put-downs whenever the crop match flickers; (b) disappears
  and the hand was moving down / stopped near a surface (landmark motion) —
  fewer false events, more logic; (c) disappears and the object is then
  matched in a crop **below** the hand on the next frames — most reliable,
  most compute. Start with (a), measure, then decide.
- **Prompt templates for text embeddings.** Options: (a) object name only;
  (b) "a photo of a hand holding {object}"; (c) an average of several
  templates. Known to matter for CLIP-style models; a quick comparison on the
  tuning session decides.
- **Unknown objects in hand.** Options: (a) ignore — only vocabulary objects
  produce events; (b) emit `object: unknown` events with the crop saved —
  lets the user name new objects later (useful for Phase 4.1); (c) emit only
  if the hand holds something for long. The draft uses (a) for the probe.

## You test this

1. Run `task perception-debug` on the tuning session. Watch the contact
   sheet: are hands boxed correctly? Is the right object at the top when
   you are clearly holding it?
2. Hold each vocabulary object in front of the laptop webcam (or record a
   1-minute phone clip) and check the top-1 match per object. Which objects
   get confused with each other?
3. Look at the per-stage cost table. Which stage is most expensive?

## How this number could be lying

- Thresholds tuned on one session and tested on another from the same room
  with the same objects will look better than on new rooms. Step 19 reports
  results on sessions not used for tuning; held-out rooms come in Phase 4.1.
- The image-text model may recognise the object from the background (keys
  are often on the key hook), not from the hand. The debug view shows
  crops so this can be spotted.
- Laptop cost per stage is not phone cost; Step 22 measures the phone.

## Verification

- [ ] `src/perception/` files each under 300 lines; settings in
      `src/config.py`.
- [ ] Runner writes valid slot records (`validate_slot` passes on all).
- [ ] Thresholds tuned only on the designated tuning session, frozen and
      recorded before Step 19.
- [ ] Per-stage cost table produced.
- [ ] Debug contact sheet produced and reviewed by the user.

## Files changed

- [NEW] `src/perception/__init__.py`, `hands.py`, `crop_match.py`,
  `interactions.py`, `runner.py`
- [MODIFY] `src/config.py` — `MEMORY_PERCEPTION_*` settings
- [MODIFY] `.env.example`
- [MODIFY] `Taskfile.yml` — `perception-run`, `perception-debug`
- [MODIFY] `README.md`

## Dependencies

- Step 02 (slot schema), Step 17 (chosen models and any approved
  dependencies), Step 05 (session vocabularies).

## Common issues

- Hands partly out of frame on a chest mount: crops get cut at the edge.
  Pad with border pixels and record how often it happens.
- Two hands holding one object (a box): both produce matches; merge events
  of the same object within a short time.
- Very small objects (a ring) occupy a few pixels in a 640×480 crop; this is
  the expected failure and must appear in results, not be tuned away.
