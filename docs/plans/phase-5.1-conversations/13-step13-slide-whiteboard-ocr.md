# Phase 5.1 Step 13 — Slide and Whiteboard Capture with OCR

## What

For lectures and meetings with a screen or whiteboard:

1. **Slide-change keyframes**: during a session with the camera on (phone on
   the desk facing the board), detect when the board content changes, reusing
   the Phase 4 Tier 0a change gate and Tier 0b blur gate on a board region,
   and keep one sharp keyframe per slide / board state.
2. **OCR**: read text from each keyframe with an on-device OCR engine
   (shortlisted here with licence and phone artifact checks).
3. **Storage**: slide keyframes as slot records (`kind: text_seen`,
   `producer.path: ocr`) linked to the session and time; text indexed for
   search.
4. **Evaluation** on the Phase 3.1 lecture session(s): slide-change recall and
   precision against `slides.json` (±5 s), OCR character error rate (CER) and
   word error rate against the slide text.

## Why

- Roadmap v2: "slide and whiteboard capture: slide changes are keyframes,
  text read by OCR". Lecture questions often ask about what was on a slide.
- Reusing the Phase 4 gates shows the cascade is a general component, not
  only for daily-life video.
- OCR is another place where an LLM-free method may do better than a VLM
  reading text from a small image; the VLM comparison is optional and cheap
  on a few frames.

## How to implement

1. **Board region**: either the whole frame or a user-marked rectangle at
   session start (simple drag on the phone preview); stored in session meta.
2. **Change detection**: Tier 0a on the region with a threshold tuned for
   slides (larger, sudden changes); Tier 0b keeps the sharpest frame within a
   few seconds after a change; people walking in front of the board are
   handled by requiring the change to persist (as in Phase 4 Step 10's
   look-ahead option).
3. **OCR shortlist** (to verify: licence text, phone artifact, laptop
   runtime): Tesseract (laptop; Android builds exist), PaddleOCR mobile
   models, Google ML Kit text recognition (on-device, Android only — parity
   issue), as listed in Phase 4 Step 09's OCR open decision. Hard filters as in
   Phase 3.1 Steps 17 and 20.
4. **`src/conversations/slides.py`**: change detection over a session's
   frames, keyframe selection, OCR call, slot records.
5. **Evaluation script** with CER / WER (reusing the WER code from Phase 3.1)
   and slide-change matching.

## Open decisions

- **OCR engine.** Options: (a) the same open model on laptop and phone
  (PaddleOCR mobile or Tesseract) — parity, more integration work; (b) ML Kit
  on the phone, Tesseract on the laptop — easy on the phone, results differ
  between platforms; (c) the VLM reads slides — no new model, slow and
  possibly weak on small text. This continues Phase 4 Step 09's open
  decision; whichever is chosen applies to both.
- **Camera during meetings.** Options: (a) only for lectures; (b) optional for
  meetings with a screen; (c) never in meetings (privacy). Draft: (a) plus (b)
  when everyone agreed to video.

## You test this

1. In the lecture recording, scroll the detected slide keyframes. Did it catch
   every slide change? Any duplicates?
2. Compare the OCR text of 5 slides with the real slides; mark errors.

## How this number could be lying

- Projected slides photographed from a desk vary hugely with distance and
  angle; one lecture room is one condition. State it.
- CER on large title text is much better than on small body text; report
  both if the slides allow.

## Verification

- [ ] OCR shortlist with verified licences and phone artifacts.
- [ ] Slide-change precision / recall and OCR CER / WER on the lecture
      session(s).
- [ ] Slide text searchable through memory search.
- [ ] Works on the Pixel on a recorded lecture (full parity in Step 18).

## Files changed

- [NEW] `src/conversations/slides.py`
- [NEW] `docs/results/phase-5.1/ocr-shortlist.md`,
  `docs/results/phase-5.1/step13-slides.md`
- [MODIFY] `docs/results/phase-3.1/licence-ledger.md`, `src/config.py`
- [MODIFY] `pyproject.toml` only with approval, `README.md`

## Dependencies

- Step 02 (sessions with camera), Phase 4 Steps 05–06 (gates), Phase 3.1
  lecture recording and `slides.json`.

## Common issues

- Slide animations (bullets appearing one by one) create many small changes;
  keep the last state before a large change, or all states with a merge rule.
