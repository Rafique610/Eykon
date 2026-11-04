# Step 09 — Tier 2: Structured VLM Extraction (Provisional → Refined)

> [!IMPORTANT]
> **Roadmap v2 — 07 October 2026 (additions only):**
> - The structured record below is replaced by the **slot schema v1**
>   (`src/memories/slots.py`, Phase 3.1 Step 02). Same idea, fixed field
>   names, validated. The prompt starts from `src/vision/slot_prompt.py` and
>   the Probe A findings (Phase 3.1 Step 16): if Probe A found the slot prompt
>   worse than free captions, that is addressed here first.
> - **Two paths, one record.** Tier 2 is an interface
>   `extract(frame_or_event) -> SlotRecord` with two implementations:
>   path V (this doc, VLM) and path C (cheap perception from Phase 4.1,
>   `src/perception/`). A setting `MEMORY_EXTRACTION_PATH=vlm|cheap|both`
>   chooses. The bounded queue and drop policy apply to path V; path C is
>   expected to run inline (to be measured).
> - The "Provisional model" open decision gains option (d): path C as the
>   provisional record, VLM as the asynchronous refinement — cheap and
>   immediate, refined later.
> - Verification adds: both paths produce records that pass `validate_slot`
>   on the golden fixtures.

## What
When Tier 1 fires, the heavy model produces a **structured record** instead of
a free sentence, e.g.

```json
{"place": "home office", "action": "typing", "objects": ["laptop", "keys", "mug"],
 "hand_object": "placing keys on desk", "text_visible": ["Pull Request #42"],
 "caption": "Placing keys on the desk next to the laptop."}
```

Borrowing LightMem-Ego's idea: a fast **provisional** record is written
immediately (cheap model or slots-only prompt), and an optional **refined**
record is attached asynchronously when compute is free. The VLM runs behind a
**bounded queue** with an explicit drop policy.

## Why
- Free captions are verbose and inconsistent → noisy retrieval and no handle
  for Phase 5's entity-state tracking (`objects`, `hand_object` feed it).
- Synchronous captioning at 13 s/frame cannot keep up live; async + bounded
  queue makes the backlog visible and controlled instead of silent.

## How to implement
- `src/vision/extract.py`: prompt templates per model; JSON parsing with
  fallback (if JSON invalid → store raw caption, flag `parse_failed`).
- Constrained decoding where the runtime supports it (llama.cpp GBNF grammar);
  LiteRT-LM: prompt-only + validation.
- Bounded `queue.Queue(maxsize=K)`; on full: drop oldest *provisional-only*
  job, never a job the segmenter marked as event start. Log drops.
- Optional OCR sub-step when Tier 1 flags text-heavy scenes (option below).
- Experiment: free caption vs. structured on the same keyframes →
  downstream R@3 / QA accuracy + parse-failure rate + tokens/latency.

## Open decisions
- **Provisional model**: (a) SmolVLM-256M slots-only prompt — fast, weak
  detail; (b) the A8 winner for both provisional and refined — simpler, slower;
  (c) no provisional, only queue — simplest, but memory is empty until the
  queue drains.
- **OCR**: (a) none — VLM reads text itself (often badly at low res);
  (b) ML Kit text recognition on phone / Tesseract on laptop — parity issue,
  different engines; (c) PaddleOCR mobile on both — same model both sides,
  heavier integration.
- **Constrained decoding**: (a) grammar (llama.cpp) — guaranteed JSON, slower
  sampling; (b) prompt + validation + retry once — runtime-agnostic.

## You test this
- I show you 30 keyframes with their structured records. Mark each field
  correct/wrong. Especially check `hand_object` — it's the hardest and the most
  valuable.
- Then ask 10 questions of your choice on the kitchen session and judge the
  answers — free-caption DB vs structured DB, blind (you don't know which is which).

## How this number could be lying
- Structured slots can look precise while being hallucinated ("keys" listed
  because the prompt mentions keys) → never put example objects from the QA set
  into the prompt.
- JSON validity rate on laptop F16 may drop on Q4 phone models → measure on the
  exact phone artifact at the parity gate.

## Verification
- [ ] Parse success rate ≥ 95 % (or documented why not).
- [ ] Field-level human accuracy table.
- [ ] Free vs structured downstream comparison on tuning QA set.
- [ ] Queue backlog and drop counts under wall-clock replay reported.

## Files changed
- [NEW] `src/vision/extract.py`, `tests/test_extract.py`
- [MODIFY] `src/vision/captioner.py` (reuse loader), `src/config.py`, `README.md`

## Dependencies
- Step 08; Phase 3 Step 14 (provisional model choice).

## Common issues
- Small VLMs ignore JSON instructions → few-shot with neutral examples, or slots
  extracted by a second tiny text-only pass from a free caption.
