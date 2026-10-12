# Phase 3.1 Step 02 — Slot Schema v1 (the Perception to Memory Contract)

## What

Define one fixed record format, called a **slot record**, that every
perception path must write, no matter what produced it:

- the VLM path (Gemma 4 E2B or another small VLM, asked to fill fields
  instead of writing a free caption),
- the cheap path (hand tracker + crop matching + image-text embeddings, no
  language model),
- later: speech (Phase 5.1), OCR (Phase 5.1), faces (Phase 6.5).

A slot record is a small JSON object with named fields ("slots"): when, what
was seen, what was held, what changed, who produced it, how confident it is.
Memory (Phase 5) only reads slot records; it never needs to know which model
wrote them.

Deliverables:

- `src/memories/slots.py`: a `SlotRecord` dataclass (and a few small nested
  dataclasses), `to_dict` / `from_dict`, and `validate_slot(d) -> list[str]`.
- `docs/results/phase-3.1/slot-schema-v1.md`: every field explained in plain
  language with one example per producer.
- `data/golden/slots/`: 6 hand-written example records (2 VLM, 2 cheap path,
  2 speech) used as golden fixtures by Python now and Kotlin later.

## Why

- **Fair comparison** (roadmap v2 design principle 2). Probe B and Phase 5.2
  compare "VLM path" with "cheap path". If one writes a paragraph and the
  other writes `{"object": "keys", "in_hand": true}`, there is no fair way to
  score them. Same fields means same scorer.
- **LLM-optional design.** If memory reads only slots, swapping the VLM for
  the cheap path (L0 vs L3 in Phase 5.2) is a configuration change, not a
  rewrite.
- **The current pipeline writes free text.** `src/vision/processor.py`
  produces `CaptionedFrame.caption` (a sentence prefixed with a timestamp),
  stored as `MemoryRecord.text`. Phase 4 Step 09 already wanted "JSON slots vs
  free caption"; this step fixes the format early so the probes can use it.
- **Phone parity.** The same JSON shape is easy to write from Kotlin and to
  check against the golden fixtures.

## How to implement

1. **Draft the fields.** Starting point (to be confirmed in this step):

   | Field | Type | Meaning | VLM path | Cheap path |
   |---|---|---|---|---|
   | `schema_version` | str | `"slot-v1"` | yes | yes |
   | `record_id` | str | unique id (uuid4) | yes | yes |
   | `session_id` | str | which recording / live session | yes | yes |
   | `t_start`, `t_end` | float, seconds from session start | time span covered (equal for a single frame) | yes | yes |
   | `wall_time` | ISO string or null | real clock time if known | yes | yes |
   | `frame_refs` | list[str] | paths or ids of evidence frames | yes | yes |
   | `kind` | enum | `observation` / `interaction` / `speech` / `text_seen` | observation | interaction or observation |
   | `place` | object or null | `{label, confidence, source}`; label from place vocabulary or `null` | yes | yes (Phase 4.1) |
   | `objects` | list | each `{name, size_class, in_hand, bbox, confidence}`; `bbox` optional | yes, no bbox usually | yes, with bbox |
   | `interaction` | object or null | `{verb, object, from_place, to_place, confidence}`; verbs: `pick_up`, `put_down`, `carry`, `take`, `place` | sometimes | yes |
   | `text_seen` | list[str] | words read in the frame (OCR or VLM) | yes | OCR only |
   | `speech` | object or null | `{speaker, text, lang, confidence}` | no | no (speech producer) |
   | `caption` | str or null | optional free sentence, kept for retrieval and comparison | yes | no (null) |
   | `producer` | object | `{path: "vlm"\|"cheap"\|"asr"\|"ocr", model, model_version, config_hash}` | yes | yes |
   | `confidence` | float 0–1 | overall confidence | yes (see open decision) | yes |
   | `cost` | object | `{latency_ms, peak_rss_mb}` measured, not estimated | yes | yes |

2. **Rules that apply to every field:**
   - Unknown is `null`, never a guess and never an empty string pretending
     to be a value.
   - Object names are lower-case singular nouns from the object vocabulary
     (Step 05 writes the per-session vocabulary); unknown objects are allowed
     but flagged `in_vocab: false`.
   - Times are seconds from session start (float). Wall time is optional,
     because pre-recorded public videos have none.
   - `confidence` must be produced by the model or a documented rule; a
     constant like `1.0` is not allowed (real data only rule).

3. **Write `src/memories/slots.py`.** Plain `dataclasses` + `json`
   (standard library, Ponytail step 3). `validate_slot` checks required
   fields, allowed enum values, time order (`t_start <= t_end`), confidence
   range, and that `producer.path` matches `kind`. Returns a list of
   problems.

4. **Bridge to the existing store.** Do not change the database in this
   step. Write one helper `slot_to_memory_text(slot) -> str` that turns a
   slot record into the text currently stored in `MemoryRecord.text`, and
   put the full slot JSON into `MemoryRecord.metadata["slot"]`. That keeps
   Phase 1 search working unchanged. Phase 5 Step 01 (schema v2) decides real
   columns.

5. **Prompt draft for the VLM path.** Write the first version of the
   "fill these slots as JSON" prompt for Gemma 4 E2B in
   `src/vision/slot_prompt.py`. Include the allowed verbs and the per-session
   object vocabulary. Probe A (Step 15) uses it. A failed JSON parse is
   recorded as a failure, not silently retried forever (max 1 retry, both
   attempts logged).

6. **Golden fixtures.** Hand-write 6 records in `data/golden/slots/` and a
   `task slots-check` that validates them. Add 4 deliberately broken records
   (`data/golden/slots/invalid/`) that must fail validation.

7. **Document** every field with a plain-language explanation and an
   example in `slot-schema-v1.md`, including a "what memory does with it"
   column so you can explain the contract to the panel.

## Open decisions

- **Where confidence comes from on the VLM path.** Options:
  (a) ask the model to output a confidence number — easy, but small models'
  self-reported confidence is poorly calibrated; (b) use token
  log-probabilities of the answer — more honest, but LiteRT-LM may not
  expose them (to be verified); (c) agreement between two prompts or two
  frames — costs double inference. Probe A measures how well whichever
  option is chosen predicts correctness.
- **Bounding boxes from the VLM.** Options: (a) never ask, `bbox` is null on
  the VLM path — simplest, comparison on presence only; (b) ask Gemma for
  boxes — enables spatial comparison but small VLMs are often poor at
  coordinates (to be measured); (c) ask only in Probe A as an extra
  measurement, not in the schema contract.
- **Object vocabulary: closed or open.** Options: (a) closed per-user list
  (keys, wallet, passport…) — matches the cheap path, easy to score, misses
  everything else; (b) open vocabulary — VLM can name anything, scoring
  needs synonym mapping; (c) open names but always mapped to the closest
  vocabulary item with a similarity score, keeping the raw name. Affects how
  fair Probe B is.
- **One record per frame or per event.** Options: (a) per frame now, events
  are built in Phase 4 Step 10 — simplest; (b) per event from the start —
  fewer records but the producer must segment; (c) both via `t_start`/`t_end`
  (a frame is an event with equal times) — the draft above already allows
  this.

## You test this

1. Open `slot-schema-v1.md` and the 6 golden records. For the "keys put on
   desk" example, check that you can read what happened without any other
   file.
2. Take one frame from your own phone gallery, and fill in a slot record by
   hand in a text editor. Run `task slots-check -- path/to/your.json`. If it
   rejects something reasonable, or accepts something wrong, tell me.
3. Run `task slots-check` and confirm: 6 valid pass, 4 invalid fail with a
   readable reason each.

## How this number could be lying

- A schema that is easy for the cheap path and awkward for the VLM (or the
  other way round) biases Probe B and Phase 5.2 before any experiment runs.
  Check: both golden VLM examples and both cheap examples fill the fields
  that matter for `object_location_*` questions.
- `cost.latency_ms` measured on the laptop is not phone latency. The field
  records what was measured where (`producer.config_hash` includes the device
  profile).
- Forcing JSON output can lower a VLM's accuracy compared with free captions.
  Probe A runs both the slot prompt and the Phase 3 free caption prompt on
  the same frames so this effect is measured, not assumed.

## Verification

- [ ] `src/memories/slots.py` under 300 lines, standard library only.
- [ ] `task slots-check` passes the 6 valid fixtures and rejects the 4
      invalid ones.
- [ ] `slot_to_memory_text` output for each fixture is readable and searchable
      by the existing `search_memories` (check: save the 6 fixtures into a
      scratch DB, query "keys", the keys record is in the top 3).
- [ ] Slot prompt parses into a valid record for at least 8 of 10 frames from
      the Phase 3 test clips (laptop, Gemma 4 E2B); failures listed.
- [ ] Field documentation has a plain-language explanation for every field.

## Files changed

- [NEW] `src/memories/slots.py`
- [NEW] `src/vision/slot_prompt.py`
- [NEW] `docs/results/phase-3.1/slot-schema-v1.md`
- [NEW] `data/golden/slots/*.json`, `data/golden/slots/invalid/*.json`
  (git-ignored by `/data/`; a copy of the fixtures is also committed under
  `docs/results/phase-3.1/golden-slots/` so the Kotlin side can use them)
- [MODIFY] `src/memories/__init__.py` — export `SlotRecord`, `validate_slot`
- [MODIFY] `Taskfile.yml` — `slots-check`
- [MODIFY] `README.md`

## Dependencies

- Step 01 (categories decide which fields must exist; e.g. `who_said` needs
  `speech.speaker`).

## Common issues

- Gemma wraps JSON in markdown fences or adds commentary. Strip fences
  before parsing; anything else is a parse failure and is counted.
- Field creep: every new idea becomes a field. Rule: a field is added only if
  a question category in Step 01 needs it.
- Float times drift when frames are re-extracted at a different fps. Always
  store times from the source video timestamps, not from frame index × interval.
