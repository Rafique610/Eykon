# Phase 5.2 Step 03 — Level T: Template Answers from the State Table, Events and Action Items

## What

Answers built from structured memory with fixed sentence templates, no model:

| Intent | Source | Template example |
|---|---|---|
| `object_location_now` | ledger current row | "Your {object} was last seen {place} at {time} [e1]." / low confidence: "Last seen in your hand at {time} [e1]; I'm not sure where it was put." |
| `object_location_past` | ledger row valid at t | "At {t}, your {object} was {place} (seen {time} [e1])." |
| `short_event` | events / interaction records in the window | "Yes — at {time} you {verb} the {object} [e1]." / "I found no record of that between {t1} and {t2}." |
| `temporal_order` | events after / before an anchor | "After {anchor} ({time}), you {event label} at {place} [e1], then {…} [e2]." |
| `activity_summary` | episodes / events in window | "{t1}–{t2}: {label} at {place} [e1]; {…}" (one line per episode) |
| `action_items` | `action_items` table | "You agreed to: 1) {task} ({time}, {session}) [e1] …" |
| `who_said` (with quote) | utterance hit | "{speaker} said it at {time} in {session}: “{quote}” [e1]." |
| `negative` | nothing above threshold | refusal text from Step 05 |

Time and place formatting (relative: "today at 2:05 pm", "about 20 minutes
ago"), pluralisation and confidence wording are shared helpers.

## Why

- Many questions are lookups. If the state table knows the keys are in the
  bag since 14:03, a template answer is exact, instant and cannot invent
  anything. This is the core of the LLM-free claim.
- Templates make failures obvious: a wrong answer comes from wrong memory,
  not from a model's wording, which makes error analysis clean.
- Templates are cheap on the Infinix (no model load, no heat).

## How to implement

1. `src/answers/templates.py`: one small function per intent, each returning
   `(text, evidence_ids, confidence)`; a formatting helper module if needed
   to stay under 300 lines.
2. Confidence rule documented per intent (for example: ledger confidence ×
   recency factor; utterance retrieval score).
3. Coverage check: run all tuning questions; count how many intents have a
   template and how many fall back (fallback rate is a result).
4. Wording reviewed by the user for clarity (plain English, no jargon).

## Open decisions

- **Hedged wording thresholds.** Options: (a) one confidence threshold for
  hedging ("probably") — simple; (b) per intent thresholds — more accurate,
  more tuning; (c) set after Step 10 calibration.
- **Templates for `meeting_summary`.** Options: (a) use the Phase 5.1
  extractive summary (quote bullets) — level Q really; (b) topic titles
  only — very short; (c) topic titles plus top quote per topic (draft).

## You test this

1. Ask 20 tuning questions at level T. Mark each answer correct / partly /
   wrong and note whether the wording is clear.
2. Find one question type where templates feel clearly worse than a natural
   answer; describe why.

## How this number could be lying

- Templates designed while looking at tuning questions fit them well; the
  held-out questions in Step 09 test generality.
- High accuracy on `object_location_now` may reflect the ledger's quality,
  not the template's; Step 12 separates "memory wrong" from "answer wrong".

## Verification

- [ ] Template for every intent listed above (or a documented fallback).
- [ ] Confidence rule documented per intent.
- [ ] Coverage and fallback rate on the tuning questions.
- [ ] Files under 300 lines, standard library only.

## Files changed

- [NEW] `src/answers/templates.py` (and `src/answers/format.py` if needed)
- [NEW] `docs/results/phase-5.2/step03-templates.md`
- [MODIFY] `README.md`

## Dependencies

- Steps 01, 02; Phase 5 Step 07 (ledger), Step 05 (episodes), Phase 5.1
  Steps 10, 12.

## Common issues

- Places stored as cluster ids without names: show "the place in this
  picture [e1]" instead of an id.
