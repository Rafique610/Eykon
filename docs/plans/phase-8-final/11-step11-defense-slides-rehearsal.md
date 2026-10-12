# Phase 8 Step 11 — Defense Slides and Rehearsal with a Question Bank

## What

1. **Slides** (length per department rules), following the thesis argument:
   problem and use cases → what changed since the first defense → architecture
   → the four research problems with one key result each → the LLM question
   (L0–L3 result) → live phone results → limitations → conclusion; every
   number from the final results with its interval.
2. **Question bank**: at least 40 likely panel questions with short answers
   and the slide or result file that supports each, including the hard ones:
   "do you really need an LLM?", "how is this different from LightMem-Ego?",
   "what about privacy and bystanders?", "your data is only you", "what happens
   with small objects?", "why should we believe the phone numbers?", "what did
   not work?".
3. **Rehearsals**: at least 2 full mock defenses (classmates and, if possible,
   the supervisor), timed, with questions from the bank and new ones; notes on
   weak answers and fixes.

## Why

- The first defense was rejected; preparation against the panel's known
  concerns (literature, PoC strength, use case, deployment, KPIs — listed in
  the Phase 3 overview) is the most direct way to pass.

## How to implement

1. Draft slides from the one-page results summary (Step 06); figures from data.
2. Question bank as a table: question, 2–3 sentence answer, evidence link.
3. Mock defenses; update slides and answers after each.

## Open decisions

- **Slide tool.** Options: (a) the department template; (b) a project slide
  deck tool available to the user; (c) PDF export of either. Check rules
  first.

## You test this

1. Answer 10 random bank questions out loud in under 1 minute each.
2. Do the mock defenses.

## How this number could be lying

- Rehearsed answers can sound more certain than the data; every answer uses
  the same hedges as the results (intervals, limitations).

## Verification

- [ ] Slides with numbers matching final results (numbers check).
- [ ] Question bank of at least 40 entries with evidence links.
- [ ] At least 2 mock defenses with notes and fixes.

## Files changed

- [NEW] `docs/results/phase-8/slides/`, `docs/results/phase-8/question-bank.md`,
  rehearsal notes

## Dependencies

- Steps 09, 10.

## Common issues

- Too many slides on implementation details; the panel cares about the
  argument and the evidence.
