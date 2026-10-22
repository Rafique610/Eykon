# Phase 5.2 Step 01 — Answer Interface Contract

## What

One function every question goes through, whatever the level:

```
answer(request: AnswerRequest) -> Answer
```

- `AnswerRequest`: question text, parsed intent and time window (from
  Phase 5 Step 08), evidence block (from the router, Phase 5 Step 09 /
  Phase 5.1 Step 12), requested level (`T` template, `Q` quote, `X`
  extractive, `G` generative, or `auto` = the configured default), asked-at
  time, configuration id (L0–L3).
- `Answer`: text, level actually used, list of evidence items used (Step 02),
  confidence (0–1, from the level's documented rule), `refused` (bool) with a
  reason, timing (ms per stage), model calls made (count and type).
- Rules: an answer **without evidence** is only allowed when `refused` is
  true; every level returns the same structure; failures inside a level fall
  back to a lower level and the fallback is recorded.

Deliverables: `src/answers/interface.py` (dataclasses + dispatcher), a
contract document `docs/results/phase-5.2/answer-contract.md`, and the
Kotlin mirror designed (built in Step 13).

## Why

- Fair comparison needs one entry point: if L0 and L2 answered through
  different code paths with different evidence, differences in results could
  come from the plumbing, not from the level.
- Recording level, evidence, calls and timing in every answer gives Steps
  09–12 their data without extra instrumentation.
- The "no answer without evidence" rule is the project's evidence-first
  principle made enforceable in code.

## How to implement

1. Dataclasses in `src/answers/interface.py`; dispatcher maps level to the
   implementation module (Steps 03, 04, 06, 07) — a plain dictionary, no
   plugin framework (Ponytail).
2. Fallback chain: `G → X → Q → T → refuse` (each level can fall back only
   downward); the chain is configurable per configuration (Step 08).
3. Timing: `time.perf_counter()` per stage; model call counting through the
   existing `src/assistant/llm.py` wrapper (add a counter there, not a new
   wrapper).
4. Replace direct calls to the old prompt code in the Q&A paths with
   `answer(...)` (laptop UI and benchmarks), keeping old behaviour available
   as level `G` with the existing prompt so Phase 1 results are reproducible.
5. Contract document with 5 worked examples (object, conversation, summary,
   temporal, negative).

## Open decisions

- **Confidence meaning.** Options: (a) each level defines its own rule,
  documented — honest, not comparable across levels; (b) calibrate all
  levels to "probability of being correct" on the tuning set — comparable,
  needs labelled data (available after Step 10); (c) (a) now, (b) after
  Step 10. Draft: (c).
- **`auto` level behaviour.** Options: (a) fixed default from settings;
  (b) per-intent default (e.g. templates for object location, generative for
  summaries); (c) cheapest level whose confidence is above a threshold, else
  the next level up — an adaptive design that Step 09 can also evaluate.

## You test this

1. Read the contract examples. For "where are my keys?", can you see which
   evidence the answer would show?
2. Run `task ask -- "where are my keys" --level T` and `--level G` on the
   laptop memory DB and compare the two `Answer` printouts.

## How this number could be lying

- Timing measured inside Python excludes UI and model load time; the
  phone measurements in Step 11 include end-to-end time from tap to answer.

## Verification

- [ ] Interface and dispatcher under 300 lines; standard library only.
- [ ] Every answer carries level, evidence, confidence, timing, calls.
- [ ] Fallback chain works and is recorded.
- [ ] Phase 1 benchmark reproduces its Hit@5 and MRR through the new path.
- [ ] Contract document with 5 examples.

## Files changed

- [NEW] `src/answers/__init__.py`, `src/answers/interface.py`
- [MODIFY] `src/assistant/llm.py` (call counter), laptop Q&A page,
  `src/benchmarks/run.py` (use `answer(...)`)
- [NEW] `docs/results/phase-5.2/answer-contract.md`
- [MODIFY] `Taskfile.yml` (`ask`), `README.md`

## Dependencies

- Phase 5 Step 09 (router returns evidence blocks). Can be started earlier
  with the Phase 1 search as the evidence source.

## Common issues

- Old UI code reads plain strings; adapt it to `Answer.text` and show
  evidence separately instead of mixing it into the text.
