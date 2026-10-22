# Step 02 — Current Memory (Working Buffer)

## What
An in-RAM rolling buffer of the last N seconds/minutes: latest keyframes,
the open event, latest transcript lines, and the latest Tier 1 embedding.
Answers "what am I looking at now?", "what did she just say?" without touching
the DB, and optionally passes the **live frame** to Gemma 4 for present-tense
questions.

## Why
LightMem-Ego routes current-scene questions to current memory because it is the
cheapest and freshest source. Without it, a question about *now* waits for
captioning/DB writes and may answer with stale data.

## How to implement
- `src/memories/current.py`: `collections.deque(maxlen=…)` of typed items;
  snapshot method returning a compact text evidence block + optional frame.
- Persist nothing; it is volatile by design (privacy plus).

## Open decisions
- **Window length**: (a) 30 s — tiny RAM, covers "just now"; (b) 2 min —
  covers "a moment ago"; (c) adaptive to open event duration.
- **Live frame to Gemma**: (a) never — text only, cheaper; (b) only for
  present-tense intent — best answers, +image tokens latency.

## You test this
- Laptop webcam: hold up an object, ask "what am I holding?"; put it away, ask
  "what was I holding a moment ago?". Time both answers.

## How this number could be lying
- Present-tense latency on laptop hides phone image-encoder cost → measure on
  Pixel at the parity gate.

## Verification
- [ ] Buffer bounded (memory flat over 30 min).
- [ ] Present-tense questions answered without DB hits (log shows level=cur).

## Files changed
- [NEW] `src/memories/current.py`, tests

## Dependencies
- Step 01; Phase 4 Step 10.
