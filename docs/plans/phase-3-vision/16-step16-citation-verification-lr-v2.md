# Step 16 — Citation Verification & Literature Review v2

## What
Verify every paper cited in `new_Dev.md` and `docs/additional/literature-review.md`,
then write **LR v2** (`docs/additional/literature-review-v2.md`) organised
around our four research problems (P1–P4 in `docs/plans/00-roadmap.md`).
The original LR stays untouched.

## Why
- `new_Dev.md` was produced in a brainstorming chat. Some citations could not be
  found ("Mem-Alpha", "TokenPilot", "EgoLife: on Edge Devices"), and some
  numbers attributed to LightMem-Ego don't match its paper body
  (paper: R@3 74.1, MRR 0.627, QA 51.9 % LLM / 55.6 % human, P50 5.86 s phone
  short-term, 14.87 s long-term). One fake citation in front of a panel can sink
  the whole defense.
- LR v1 has generic references (several look unverifiable too, e.g. "Xu et al.
  2024, Efficient Memory Management for On-Device AI, IEEE TMC" and "Zhang et
  al. 2023 Thermal-Aware Scheduling for Mobile NPUs, ISCA"). Check them as well.

## How to implement
1. Build `docs/additional/citation-ledger.md` with one row per citation:

   | Cited as | Found? | Exact title / venue / year / arXiv id | Link | Claim we use it for | Claim verified in paper? (section/table) | Keep / fix / drop |
   |---|---|---|---|---|---|---|

2. Verify against arXiv / ACL Anthology / CVF / DOI — read the claim in the
   paper, don't trust summaries.
3. Seed list (from LightMem-Ego's own reference list, already confirmed to
   exist): LightMem-Ego, LightMem, Mem0, MemGPT, EgoLife, EgoMemory (ACL
   Findings), Vinci (IMWUT), Supermemory-VQA, EgoMemReason, AutoLife (IMWUT),
   VideoAgent (ECCV 2024), WorldMM, Ego-R1, VisionClaw, MobileMem.
   From `new_Dev.md` to verify: PalmBench, PowerInfer-2, MobileAIBench,
   MobileLLM, LLM in a Flash, Embodied VideoAgent, HippoRAG, MemoryBank, AKS,
   LION-FS, KNA-SG, Ego4D, DailyLLM, EdgeRAG.
4. Write LR v2 with sections: (1) egocentric memory systems, (2) keyframe /
   event segmentation (P1), (3) memory hierarchy, consolidation, forgetting,
   state updates (P2), (4) on-device inference, thermal, energy (P3),
   (5) wearable split computing (P4), (6) gap table: *system × {on-device,
   continuous capture, hierarchical memory, state invalidation, privacy}*.
5. Each section ends with "How this shapes our design" and "What we do that
   they don't".

## Open decisions
- **Citation style**: (a) IEEE numeric — standard for CS FYP reports;
  (b) APA author-year — easier to read in a long LR; (c) whatever the
  department template mandates — check the FYP handbook first, it overrides.

## You test this
- Pick 5 random rows from the ledger and open the link yourself; confirm the
  claim is really in the paper. If any fails, the whole ledger is re-checked.
- Read LR v2's gap table and tell me if any competitor you know of is missing
  (e.g. something your supervisor mentioned).

## How this number could be lying
- "Found on arXiv" ≠ "says what we claim". The ledger has a separate column for
  claim verification.
- Reported numbers from other papers are on *their* data and hardware — LR v2
  must never put their numbers and ours in one table as if head-to-head.

## Verification
- [ ] 100 % of citations in LR v2 have "Found = yes" and "Claim verified = yes".
- [ ] Every dropped citation is listed with the reason.
- [ ] `new_Dev.md` is left unchanged; corrections live in the ledger.

## Files changed
- [NEW] `docs/additional/citation-ledger.md`
- [NEW] `docs/additional/literature-review-v2.md`

## Dependencies
- None (can run in parallel with Steps 11–14).

## Common issues
- arXiv HTML may be unavailable for some papers — use the PDF.
- Paywalled venue papers: cite the arXiv preprint and note it.
