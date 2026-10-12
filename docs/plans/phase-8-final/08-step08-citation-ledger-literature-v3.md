# Phase 8 Step 08 — Citation Ledger and Literature Review v3

## What

1. **Citation ledger**: continue the ledger started in Phase 3 Step 16 — every
   reference with title, authors, venue / arXiv id, year, link, date checked,
   the exact claim we cite it for, and the page / section where that claim
   appears. Only verified entries may be cited.
2. **Check script**: scans the thesis draft for citation keys and fails if any
   key is not in the ledger or is marked unverified.
3. **Literature review v3**: updated from v2 with the topics added since
   (scenario packs, meeting summarisation and diarization on device, hand-object
   interaction detection, LLM-free vs LLM answer comparisons, split computing
   for wearables), using only verified sources; each section ends with how
   Eykon differs.
4. **Citation style**: from the department handbook (open decision in handoff
   §6).

## Why

- The handoff and roadmap flag unverifiable citations and mismatched numbers
  in `new_Dev.md` (for example papers that could not be found, and LightMem-Ego
  numbers that differ from the paper). A thesis with one fabricated citation can
  fail; the ledger and check script prevent it.
- The first literature review was judged weak by the panel; v3 must be
  specific and verified.

## How to implement

1. Ledger as a table in `docs/results/phase-8/citation-ledger.md` (or the
   Phase 3 Step 16 file, continued).
2. Check script `src/benchmarks/citation_check.py` (reads the thesis source
   format chosen in Step 09).
3. Literature review written section by section, each source read (at least
   the relevant sections) before citing.

## Open decisions

- **Citation style.** Options: (a) the style required by the department
  handbook (check first); (b) IEEE (common in CS); (c) APA. Draft: (a).
- **Reference manager.** Options: (a) a BibTeX file kept with the ledger;
  (b) Zotero exported to BibTeX; (c) plain list in the thesis tool.

## You test this

1. Pick 5 random citations and open their sources: does the cited claim really
   appear where the ledger says?

## How this number could be lying

- Verified existence is not verified claim; the ledger records the exact claim
  and location, which is what the spot check tests.

## Verification

- [ ] Every thesis citation in the ledger and verified.
- [ ] Check script passes on the final thesis.
- [ ] Literature review v3 complete with "how Eykon differs" per section.
- [ ] Citation style follows the handbook.

## Files changed

- [NEW] `docs/results/phase-8/citation-ledger.md`, `src/benchmarks/citation_check.py`,
  `docs/results/phase-8/literature-review-v3.md`

## Dependencies

- Phase 3 Step 16 (ledger v1, literature review v2).

## Common issues

- Citing a preprint when a peer-reviewed version exists; prefer the published
  version and note both.
