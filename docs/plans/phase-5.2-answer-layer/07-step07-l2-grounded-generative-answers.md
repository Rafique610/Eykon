# Phase 5.2 Step 07 — L2: Grounded Generative Answers with Citation Enforcement

## What

Level G: the generative model (Gemma 4 E2B through LiteRT-LM, the model the
app already uses) writes the answer from the evidence block, under rules that
keep it checkable:

1. **Prompt**: the question, the asked-at time, the evidence items numbered
   `[e1]…[eN]` with their times, places, speakers and confidence, and strict
   instructions: answer only from the evidence; cite `[eK]` after every
   claim; say "I don't know" if the evidence does not answer it; keep it to
   1–3 sentences (or bullets for summaries).
2. **Validation**: parse citations; every sentence must cite at least one
   valid id; uncited sentences and unknown ids are flagged; a support check
   (embedding similarity between each sentence and its cited items, as in
   Phase 5.1 Step 09) flags likely unsupported sentences.
3. **Action on failure**: one retry with a shorter, stricter prompt; if it
   still fails, fall back to level Q / T and record the fallback.
4. **Reuse**: prompt building and model calls through the existing
   `src/assistant/` code (`prompt.py`, `llm.py`); the evidence formatting is
   new.
5. **Measure**: citation validity rate, flagged-sentence rate, latency and
   tokens, on laptop (phones in Step 11).

## Why

- L2 is the "LLM for answers only" configuration (roadmap v2 §3). For a fair
  comparison it must use the same evidence as L0 and be held to the same
  evidence-first rule.
- Citation enforcement turns a generative model from "trust me" into "check
  me", which is the only defensible way to use a 2B model for answers.
- Measuring failure and fallback rates shows how often the generative level
  actually delivers on its promise.

## How to implement

1. `src/answers/generative.py`: `build_prompt(request)`, `generate(prompt)`
   (via `src/assistant/llm.py`), `validate(text, evidence)`.
2. Prompt variants kept in one place with ids; the chosen variant frozen
   before Step 09 (no prompt tuning on evaluation questions).
3. Generation settings (temperature, max tokens) from settings; deterministic
   setting for evaluation, documented.
4. Evidence budget: maximum items and tokens, as in Phase 5 Step 09.
5. Summary questions: reuse Phase 5.1 Step 09 generative summaries rather
   than generating again at question time.

## Open decisions

- **Retry policy.** Options: (a) no retry — fall back immediately, cheaper;
  (b) one retry (draft); (c) up to two retries — better success rate, slower
  and hotter on phones.
- **Answer length.** Options: (a) one sentence; (b) up to three sentences
  (draft); (c) per intent.
- **Asked-at time in the prompt.** Options: (a) always (draft) — needed for
  "now" questions; (b) only for time-sensitive intents — shorter prompts.

## You test this

1. Ask 10 questions at level G and level T / Q side by side (blind order).
   Which do you trust more, and why?
2. Find an answer where a sentence is flagged as unsupported. Was the flag
   right?

## How this number could be lying

- Gemma may follow the citation format well on clean evidence and poorly on
  messy transcripts; results per category show this.
- Laptop and phone model artifacts must be the same file; if the laptop uses
  a different quantisation, results do not transfer (roadmap §4.1 "same
  artifacts").

## Verification

- [ ] Prompt variant frozen before Step 09 (hash recorded).
- [ ] Citation validity, flagged-sentence and fallback rates on tuning
      questions.
- [ ] Latency and tokens per question on laptop.
- [ ] Same model file as the phone (hash check).

## Files changed

- [NEW] `src/answers/generative.py`
- [MODIFY] `src/assistant/prompt.py` (evidence formatting helper, if
  shared), `src/config.py`
- [NEW] `docs/results/phase-5.2/step07-l2.md`
- [MODIFY] `README.md`

## Dependencies

- Steps 01, 02, 05.

## Common issues

- The model copies the citation format wrongly (`(e1)`, `[E1]`); parse
  leniently for known variants but count them.
