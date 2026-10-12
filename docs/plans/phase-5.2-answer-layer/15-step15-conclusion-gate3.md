# Phase 5.2 Step 15 — Conclusion and Gate 3

## What

Write the answer to the panel's question, using only the Step 12 numbers and
the Step 09 decision rule, and decide the final system claim:

1. **Conclusion document** `docs/results/phase-5.2/conclusion.md` (about
   3–4 pages, plain language), following the template committed in Step 09:
   - for each category group: which configuration is best, by how much, at
     what cost, and whether the generative model is "needed" by the
     pre-registered rule;
   - what the generative model adds where it helps (from paired comparisons
     and failure codes), and what it costs (latency, battery, heat, made-up
     content rate);
   - what L0 cannot do at all (template gaps, memory gaps);
   - the honest limits of the comparison (our data, our questions, two
     phones, mock meetings);
   - written in full **whichever way the data points**, including "no LLM is
     needed for most questions" or "the LLM is needed for most questions".
2. **Gate 3 decision** (roadmap v2 §6): the final system claim (for example
   "LLM-optional: templates and quotes by default, generative answers for
   summaries and why-questions") and the app's default answer level.
3. **Supervisor review** of the conclusion; outcome recorded.
4. **Annotations**: master roadmap (Gate 3 outcome), Phase 6 overview
   (which configuration Phase 6 runs live), Phase 8 overview (which claim the
   thesis defends).

## Why

- This is the project's direct answer to "do you really need an LLM?".
  Writing it from pre-registered rules makes it defensible whatever it says.
- Phase 6 must run the configuration that will be defended; deciding it here
  avoids testing one thing live and defending another.

## How to implement

1. Fill the template with generated tables (no retyped numbers).
2. Write the narrative per category group; one paragraph each.
3. State the decision and default level; note any disagreement between the
   rule and the user's or supervisor's preference, and why.
4. Annotate later phase docs.

## Open decisions

- **If the rule and the supervisor disagree.** Options: (a) follow the rule
  and record the disagreement; (b) follow the supervisor and record the rule's
  verdict; (c) run the allowed extension (more held-out questions) once, then
  decide.

## You test this

1. Explain the conclusion to a friend in two minutes without slides. Could
   they repeat back when the LLM is needed?
2. Mark every sentence you could not defend against "how do you know?".

## How this number could be lying

- Conclusions simplify; every claim in the document links to its table row
  and interval.
- A clear conclusion from one dataset may not hold for other users; the
  limits section says so.

## Verification

- [ ] Conclusion written from the template with generated tables.
- [ ] Gate 3 decision and default level recorded.
- [ ] Supervisor review outcome recorded.
- [ ] Roadmap, Phase 6 and Phase 8 overviews annotated.

## Files changed

- [NEW] `docs/results/phase-5.2/conclusion.md`
- [MODIFY] `docs/plans/00-roadmap.md`, `docs/plans/phase-6-live/00-*.md`,
  `docs/plans/phase-8-final/00-*.md` (annotations)
- [MODIFY] `README.md`

## Dependencies

- Steps 12, 14.

## Common issues

- Waiting for perfect numbers. If a category is "unclear", say so; Phase 8's
  final held-out test can revisit it.
