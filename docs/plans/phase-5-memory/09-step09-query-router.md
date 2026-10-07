# Step 09 — Query Router

## What
Route each parsed query to the **cheapest sufficient** source (LightMem-Ego):
current memory → ledger → short-term events/transcripts → episodes → semantic
facts, with fan-out when confidence is low. Build one compact evidence block
(with timestamps + thumbnails) for Gemma 4.

## Why
Searching everything every time costs latency and adds distractors that small
LLMs get confused by. LightMem-Ego shows short-term queries P50 5.86 s vs
long-term 14.87 s on phone — routing matters for latency.

## How to implement
- Rules from Step 08 intent + time window (e.g. `current_state` → cur + ledger;
  window within last hour → short-term; older/summary → episodes/semantic).
- Confidence = top score margin; below threshold → fan-out to next level.
- Evidence budget: max K items / max tokens; dedupe by event id.
- Log route + evidence per query for evaluation.

## Open decisions
- **Router type**: (a) rules — transparent, easy to defend; (b) small classifier
  trained on our QA — adapts, needs labelled data; (c) LLM decides — flexible,
  slow on phone.

## You test this
- 20 mixed questions; for each, the UI shows which levels were searched and
  why. Flag any route that seems wrong to you.

## How this number could be lying
- Router accuracy can be high while answers stay wrong (good route, bad
  evidence) → report end-to-end QA, not only routing accuracy.

## Verification
- [ ] Routing accuracy vs gold category; latency per route on laptop + phone.
- [ ] Ablation: router vs "search all levels".

## Files changed
- [NEW] `src/memories/router.py`, tests
- [MODIFY] `src/memories/service.py`, `src/assistant/prompt.py`

## Dependencies
- Steps 02–08.
