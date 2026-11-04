---
name: explain-pipeline
description: Explain the Eykon phone video pipeline end to end, in specifics, for supervisor or panel questions. Use when the user says "explain me the end to end pipeline", "explain the pipeline", or asks how a specific stage, model, embedding, search or score works.
---

# Explain the pipeline

The supervisor asks in specifics ("which seconds are those 5 frames?", "how is
likeness calculated?"). Answer the same way: exact values, read from the code
that is on disk now.

## Rules

- **Read the source every time.** Never answer from memory, old chats or
  flow diagrams. The code in `android/app/src/main/java/com/eykon/memory/`
  (`video/`, `ml/vision/`) is the truth. Cite `file:line` for every constant.
- **Real numbers only.** Timings and accuracy come only from `docs/results/`
  or `.memory/*/tasks.md`, with the file name and the device (laptop or
  Pixel). If nothing was measured, say "not measured".
- **Format:** short bullets, grouped by stage. No essay paragraphs. Each
  bullet answers one thing: what, the exact value, why.
- **Be honest about gaps.** If the app does something the supervisor might
  not expect, or does not do it (for example the app does not show which
  seconds the kept frames come from), say so under "Known gaps".
- If the user asks about one stage only, answer only that stage, at the
  same depth.

## What the full answer covers, in this order

For each stage: input → what happens → exact values (sizes, cut-offs,
counts) → output (table and columns) → why this choice (the benchmark or
decision that picked it, with its result file).

1. **Add a video**: what is saved, where, which `videos` columns
   (recorded time, duration, GPS), job queue and stage order
   (`VideoPipeline.kt`), what happens on failure and Retry.
2. **Split**: how frames are decoded (every 30 fps frame or only some),
   which times are kept (fps, formula), size and JPEG quality, the WAV
   format.
3. **Frame filters**: each check (dark, bright, blurry, unchanged) with its
   cut-off and how it is measured; the slot size; "sharpest of the slot".
   Worked example: a 15 s clip gives X decoded → Y checked → Z kept, and
   **which seconds** were kept, with the reason for each drop.
4. **Duplicates**: dHash bits and cut-off, MobileCLIP cosine cut-off,
   which frame survives.
5. **Describing a frame**: for each model (YOLOX-Tiny COCO, D-FINE S
   Objects365, YOLOE-11L with its word list, MobileCLIP place and action
   prompts): what it detects, the label set, input size and letterbox or
   stretch, score cut-off, NMS, how the results merge, how the caption is
   built. Include a real caption example from the phone.
6. **Embeddings**: which model makes which vector (MobileCLIP-S2 image
   512-d, bge-small 384-d for captions), normalisation, how it is stored
   (float32 BLOB, table and column), when it is loaded into memory.
7. **Query path**: typed text → CLIP BPE tokenizer (77 tokens) →
   MobileCLIP text encoder → 512-d vector → dot product with every stored
   frame vector → top-N → ready videos only → shown results. Also say which
   indexes exist but are not used by search yet (keyword, caption vectors).
8. **Likeness**: the exact formula (cosine = dot product of unit vectors),
   the typical range seen on the phone, what pushes it up or down (prompt
   wording, object size in the frame, blur, lighting, the frame crop), and
   that it is not a probability.
9. **Latest sighting**: how a crop is matched across videos (crop cosine
   cut-off, minimum box side).
10. **Result card**: every field shown and where it comes from.
11. **Model choices**: for each model, the candidates tried, the result
    that won (found / false finds / seconds per frame, with device), the
    licence, and the result file.
12. **Known gaps and next changes**: what is built but unused, what is
    not built (speech, sounds), open cards.

End with a two-line summary of the whole path, and offer the stage the
user most likely needs next.
