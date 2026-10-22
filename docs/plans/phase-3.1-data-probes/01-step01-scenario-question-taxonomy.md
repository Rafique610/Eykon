# Phase 3.1 Step 01 — Scenario and Question Taxonomy v2

## What

Write down, precisely, every kind of question Eykon must answer, grouped by
scenario pack. For each question category define:

- a short id (used in files and result tables),
- a plain-language definition and 3–5 example questions,
- the **answer type** (a place, a time, a yes/no, a name, a list, a summary,
  "I don't know"),
- the **evidence type** the answer must show (a frame, a time range, quoted
  words, a list of timestamps),
- how the answer is **scored** (exact match, set overlap, human judgement),
- which phase is responsible for answering it,
- the minimum number of questions in the tuning set (30) and where those
  questions come from (which recordings).

Output: `docs/results/phase-3.1/taxonomy.md` (human readable) and
`src/scenarios/taxonomy.py` (the same ids as constants, so code and docs
cannot drift).

## Why

- The QA set (Step 12), the probes (Steps 13–21), and the final L0–L3
  comparison (Phase 5.2) all report results **per category**. If the
  categories are vague, two people put the same question in different
  buckets and the per-category numbers mean nothing.
- Roadmap v2 adds four categories (meeting_summary, who_said, action_items,
  lecture_recall) to the seven from the old Phase 4 Step 01. Those seven
  were never formally defined; each step just listed the names.
- Scoring must be decided before data is collected. "Summary" questions
  cannot be scored by exact match; deciding that now avoids discovering it
  after 300 questions are written.

## How to implement

1. **Start from the existing seven categories** (old Phase 4 Step 01):

   | id | Pack | Example | Answer type | Evidence | Scoring |
   |---|---|---|---|---|---|
   | `object_location_now` | A | "Where are my keys?" | place | frame + time of last placement | correct place (exact, with synonym list) |
   | `object_location_past` | A | "Where were my keys at 10 am?" | place | frame + time | correct place at that time |
   | `short_event` | A | "Did I take my medicine after breakfast?" | yes/no + time | frame + time | yes/no correct and time within ±10 s |
   | `temporal_order` | A | "What did I do after leaving the kitchen?" | activity | time range | human judgement (correct / partly / wrong) |
   | `conversation_recall` | A / B | "What did Sara say about the bus time?" | quote or gist | quoted words + time | human judgement + time within ±15 s |
   | `activity_summary` | A | "What did I do this morning?" | short list | list of time ranges | human judgement per item |
   | `negative` | all | "Where did I put my passport?" (never seen) | "I don't know" / "not seen" | none | correct only if the system declines |

2. **Add the four new categories** from roadmap v2:

   | id | Pack | Example | Answer type | Evidence | Scoring |
   |---|---|---|---|---|---|
   | `meeting_summary` | B | "Summarise the project meeting." | 5–10 bullet summary | each bullet links to a time range | human faithfulness audit: per bullet supported / unsupported / wrong speaker |
   | `who_said` | B / C | "Who suggested moving the deadline?" | speaker label or name | quoted words + time | exact speaker match |
   | `action_items` | B | "What did I agree to do?" | list | each item links to a time | set overlap with reference list (precision, recall) |
   | `lecture_recall` | C | "What did the teacher say about normalisation?" | gist or quote | quoted words + time, or slide frame | human judgement + time within ±30 s |

3. **Decide which phase answers each category** (needed for Phase 5.2
   tables). Draft mapping: `object_location_*` and `short_event` → Phase 4 /
   4.1 / 5 Step 07 (state table); `temporal_order`, `activity_summary` →
   Phase 5 Steps 05, 08; `conversation_recall`, `who_said`, `action_items`,
   `meeting_summary`, `lecture_recall` → Phase 5.1; `negative` → Phase 5.2
   answer layer (must refuse).

4. **Add sub-tags** that every question also carries, so results can be split
   later without re-labelling:
   - `difficulty`: `easy` (one fact, one time) / `hard` (needs two events or
     a time window),
   - `time_reference`: `none` / `absolute` ("at 10 am") / `relative`
     ("after lunch"),
   - `object_size` for object questions: `small` (fits in a closed hand:
     keys, ring, pill) / `medium` (book, phone, bottle) / `large` (bag, chair),
   - `modality_needed`: `vision` / `audio` / `both`,
   - `scripted`: true if it comes from a scripted session.

5. **Write the place vocabulary rule.** For location answers, a list of
   allowed place names per recording plus synonyms ("desk" = "table near
   the window"). Without this, "on the desk" vs "on the table" is scored
   wrong by an exact matcher.

6. **Write the scoring rules** in `taxonomy.md`, one paragraph per scoring
   method: exact match with synonym list, time tolerance, set overlap
   (precision and recall on action items), human three-way judgement
   (correct / partly / wrong) with written criteria for "partly".

7. **Code constants.** `src/scenarios/taxonomy.py` holds the category ids,
   sub-tag allowed values and per-category minimum counts as plain
   constants and one small `validate_question(q: dict) -> list[str]`
   function that returns problems (empty list means valid). No classes
   needed (Ponytail ladder step 1).

## Open decisions

- **People-pack categories now or later?** Pack D (faces, names) is stretch.
  Options: (a) leave it out of the taxonomy entirely — less work, but adding
  it later means editing the QA format; (b) reserve the ids (`person_seen`,
  `person_said`) now with zero minimum count — no extra work now, format is
  ready; (c) collect a few questions now — wasted effort if Phase 6.5 is cut.
- **Slide or whiteboard content as its own category?** Options:
  (a) fold into `lecture_recall` — fewer categories, but OCR performance is
  then hidden inside a mixed number; (b) separate `slide_content` — clean
  OCR evaluation, needs 30 more questions; (c) a sub-tag
  `modality_needed=slide` inside `lecture_recall` — middle ground, splittable
  later without a new category.
- **Time tolerance values** (±10 s, ±15 s, ±30 s above are drafts). Options:
  (a) keep the drafts; (b) derive tolerance from annotation agreement in
  Step 10 (if two annotators disagree by 6 s on average, a 5 s tolerance is
  unfair); (c) report results at two tolerances. Option (b) is the most
  defensible but can only be fixed after Step 10.

## You test this

1. Read `taxonomy.md`. For each of the 11 categories, write one question of
   your own on a sticky note without looking at the examples.
2. Put your 11 questions in categories using only the definitions. If any
   question fits two categories, or none, the definitions need fixing —
   tell me which.
3. Read the scoring rule for `meeting_summary` and say whether you would
   accept being graded that way by the panel.

## How this number could be lying

This step produces no numbers, but it decides how every later number is
grouped. The ways that can mislead:

- Categories that are too easy (e.g. `object_location_now` with only large
  objects) make averages look good. The `object_size` sub-tag exists so
  small objects are always reported separately.
- A generous synonym list turns wrong answers into right ones. The synonym
  list is written per recording **before** any system answers are seen.
- Human-judged categories drift with the judge's mood. Written criteria for
  "partly" plus double-judging a subset (Phase 5.2) keep this honest.

## Verification

- [ ] 11 categories defined, each with definition, 3–5 examples, answer type,
      evidence type, scoring method, owning phase, minimum count.
- [ ] Sub-tags and allowed values listed.
- [ ] Scoring rules written, including the "partly" criteria.
- [ ] `src/scenarios/taxonomy.py` constants match `taxonomy.md`
      (`task scenarios-check` parses the markdown table ids and compares;
      the project has no pytest, checks follow the existing Taskfile
      one-liner pattern).
- [ ] `uv run python -c "from src.scenarios.taxonomy import CATEGORIES; print(len(CATEGORIES))"` prints 11.
- [ ] User sorted their own 11 questions with no ambiguity left.

## Files changed

- [NEW] `docs/results/phase-3.1/taxonomy.md`
- [NEW] `src/scenarios/__init__.py`, `src/scenarios/taxonomy.py`
- [MODIFY] `Taskfile.yml` — `scenarios-check` task
- [MODIFY] `README.md` — new "Scenario dataset" section

## Dependencies

- None. First step of the phase.

## Common issues

- Categories multiply ("object_location_now_in_bag"…). Keep 11; use
  sub-tags for finer splits.
- `conversation_recall` and `who_said` overlap. Rule: if the expected answer
  is a person, it is `who_said`; if it is content, it is
  `conversation_recall`.
- `negative` questions must be about things that plausibly could exist
  (your passport), not nonsense ("where is my dragon"), or refusing them is
  trivially easy.
