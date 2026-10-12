# Phase 5.2 Step 06 — L1: Small Extractive Answer Model

## What

Add level X: a small model that **selects** the answer span from the evidence
text (it reads the question and the evidence and points to the words that
answer it), but cannot write new text. This defines configuration L1.

1. **Shortlist** (to verify, same hard filters as Phase 3.1 Steps 17 / 20:
   licence, phone artifact, laptop runtime, size): small extractive
   question-answering models such as MobileBERT or DistilBERT variants
   fine-tuned on SQuAD-style data; check whether an official on-device
   version exists (for example in the TensorFlow Lite / LiteRT task library
   for BERT question answering — to be verified) and what licence the weights
   carry.
2. **Integration**: `src/answers/extractive.py` builds a context from the top
   evidence items (quotes, captions, slot text), runs the model, maps the
   selected span back to its evidence item, returns the span as the answer
   with the item cited.
3. **Use**: questions whose answer is a short fact inside text ("what time is
   the bus?", "what did the teacher say normalisation reduces?").
4. **Measure**: accuracy vs level Q on the same questions; latency and memory
   on laptop (phones in Step 11).

## Why

- Roadmap v2 defines L1 as "L0 plus a small extractive answer model". It sits
  between quoting whole sentences and generating text, and is far smaller
  than a generative model.
- If L1 closes most of the gap between L0 and L2 for factual questions, it is
  a strong design option for low-end phones.
- An extractive model cannot invent text: its answers are always faithful to
  some evidence (though possibly the wrong evidence).

## How to implement

1. Shortlist table in `docs/results/phase-5.2/l1-shortlist.md`; licence rows
   in the ledger.
2. Laptop runtime: prefer an ONNX or LiteRT file runnable with an
   already-approved runtime (from Phase 3.1 / 4.1); new dependency only with
   user approval.
3. Context building: up to the model's maximum input length (often around 384
   tokens for BERT-style models — check the chosen model), ordered by
   evidence score; long contexts split into windows, best span across windows.
4. Confidence: the model's span score, calibrated in Step 10.
5. Fallback to level Q when the span is empty or below threshold.

## Open decisions

- **Which model** (from the shortlist), balancing size, accuracy on our
  questions, and phone runtime support.
- **Answer presentation.** Options: (a) the span only ("7:40 pm") — short;
  (b) span highlighted inside its sentence (draft) — shows context;
  (c) span plus the full quote card.
- **Skip L1 entirely?** Options: (a) keep L1 as a configuration — completes
  the roadmap comparison; (b) drop if no model passes the licence / phone
  filters — record why; (c) keep only for laptop comparison if no phone
  artifact exists, clearly labelled. Draft: (a), with (b) or (c) as the
  documented fallback.

## You test this

1. Ask 10 factual questions about your meetings at level X and level Q. Which
   answers do you prefer?
2. Find a question where the span is cut badly (half a time, half a name).

## How this number could be lying

- SQuAD-trained models are trained on encyclopedia text, not noisy speech
  transcripts; accuracy on our transcripts may be much lower than reported on
  benchmarks. Only our numbers are reported.
- Questions with short factual answers are easier for spans; per-category
  results show where level X does not apply at all.

## Verification

- [ ] Shortlist with verified licences and phone artifacts (or the "skip L1"
      decision recorded with reasons).
- [ ] Level X integrated with fallback to Q.
- [ ] Tuning accuracy vs level Q per category; latency and memory on laptop.

## Files changed

- [NEW] `src/answers/extractive.py`
- [NEW] `docs/results/phase-5.2/l1-shortlist.md`,
  `docs/results/phase-5.2/step06-l1.md`
- [MODIFY] `docs/results/phase-3.1/licence-ledger.md`, `src/config.py`
- [MODIFY] `pyproject.toml` only with approval, `README.md`

## Dependencies

- Steps 01, 02.

## Common issues

- Tokenizer mismatch between laptop and phone versions of the model; use the
  vocabulary file shipped with the phone artifact on both sides.
