# Phase 8 — Final Evaluation, Thesis and Defense

> Source: `docs/plans/00-roadmap.md` §6 ("Is the whole system better than the
> baselines, honestly?") and `docs/new/eykon-roadmap-v2.md` §4 (Phase 8,
> must), §5 item 9 (held-out test on new places and new meetings). Tier:
> **must**. Written 07 October 2026.

## Goal

Produce the final, defensible evidence and documents:

1. one **final held-out evaluation** on data recorded after every component was
   frozen (new places, new meetings, new questions), on both phones, comparing
   the final system with the baselines and across L0–L3;
2. a **human evaluation** with raters other than the developer;
3. the **thesis**, including an honest limitations and negative-results
   chapter and a verified literature review;
4. a **demo** that works offline in airplane mode, with a backup;
5. the **defense** slides and a rehearsed answer bank;
6. a **reproducibility package** so the results can be re-run.

## Why this phase exists

- Every earlier phase tuned something on data we had seen. A final held-out
  test after the last freeze is the only number that answers "does the whole
  system work on new days?" (roadmap pessimist rules).
- The first defense was rejected (domain index: re-defense required). This
  phase turns the work into a complete, verifiable argument for the panel.

## Steps

| # | Step | Type | Key output | Depends on |
|---|---|---|---|---|
| 01 | Final evaluation protocol and code freeze | Decision | Frozen system, protocol, pre-registered analysis | Phases 5.2, 6 (6.5 / 7 if done) |
| 02 | Final held-out dataset v3: recordings and questions | You record + write | New sessions, meetings, QA written before running | 01 |
| 03 | Final system runs on held-out v3, both phones | Experiment | All configs, all questions, both phones | 02 |
| 04 | Baseline comparisons | Experiment | Phase 1 flat RAG, uniform sampling, reference design positioning | 03 |
| 05 | Human evaluation study with independent raters | User study | Blind ratings, agreement | 03 |
| 06 | Statistical analysis and results consolidation | Analysis | Final tables with intervals, worst cases | 03–05 |
| 07 | Limitations and negative results chapter | Writing | Honest chapter | 06 |
| 08 | Citation ledger and literature review v3 | Research + writing | Verified references only | Phase 3 Step 16 |
| 09 | Thesis writing plan and chapters | Writing | Full thesis draft, supervisor reviews | 06–08 |
| 10 | Demo build, demo script and backup | Implement | Offline demo, backup video, checklist | 03 |
| 11 | Defense slides and rehearsal with a question bank | Preparation | Slides, Q&A bank, rehearsal notes | 09, 10 |
| 12 | Reproducibility package and final repository state | Engineering | README, tasks, data statement, tagged release | 09 |

## Exit criteria

- Final held-out results for every must-tier claim (keyframes P1, memory P2,
  scheduling / thermal P3, conversations, LLM-optional), on both phones, with
  intervals and worst cases, from data recorded after the freeze.
- Human evaluation with at least 3 raters other than the developer and
  agreement reported.
- Every citation in the thesis present in the verified citation ledger.
- Thesis approved by the supervisor; slides rehearsed at least twice with
  mock questions.
- Demo works in airplane mode on both phones; backup video recorded.
- Repository runs the main evaluations from the README commands.

## Risks (pessimistic)

| Risk | Likelihood | Mitigation |
|---|---|---|
| Final held-out results worse than earlier results | Medium | Expected and reported; limitations chapter explains the gap |
| Not enough time for new recordings | Medium | Recording plan in Step 02 starts as soon as Step 01 freezes; minimum sizes defined |
| Raters unavailable | Medium | Classmates booked early; short rating sessions |
| Unverifiable citations slip into the thesis | Medium | Ledger check script on the thesis text (Step 08) |
| Demo fails on the day | Medium | Backup video, second phone, pre-loaded memory database |

## Open decisions for the whole phase

- **Citation style** (handoff §6): check the department handbook first —
  Step 08.
- **Which demo** (live objects, live meeting summary, LLM-optional toggle) —
  Step 10, from Phase 6 Gate 4 results.
