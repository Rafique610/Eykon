# Phase 5.1 Step 06 — Post-Session Speaker Naming

## What

After a session, let the user turn "speaker 1, 2, 3" into names, quickly and
optionally:

1. The app shows each speaker cluster with 2–3 short audio clips (their
   clearest segments) and their total speaking time.
2. The user can type a name ("Sara"), mark "not a person" (TV, noise), merge
   two clusters ("these are the same person") or split a cluster at a chosen
   segment.
3. Names are stored per session in `speakers.user_name`; utterances,
   summaries and action items update immediately.
4. Optionally, the user can save a named speaker's voiceprint for future
   sessions ("remember Sara's voice"); this is **off by default** and is part
   of the people layer (Phase 6.5), so here it is only designed, not built,
   unless Phase 6.5 is in scope.

## Why

- "Speaker 2 suggested moving the deadline" is much less useful than "Sara
  suggested…". A 30-second naming step after the meeting gives names without
  any face or identity recognition.
- Merge and split let the user fix the most common diarization mistakes,
  which also gives us a measure of how much correction the system needs (an
  honest usability number).
- Keeping naming per session and cross-session memory opt-in respects the
  privacy rules (no automatic identification of people).

## How to implement

1. **Laptop**: a section in `src/conversations/app_page.py` (Streamlit,
   separate file) with clips, name fields, merge and split buttons.
2. **Phone**: a "Name speakers" screen opened from the session's result
   page.
3. **Data changes**: naming only updates `speakers` rows; merge re-points
   utterances from one speaker id to another; split creates a new speaker from
   a chosen time onward. All changes logged in a `speaker_edits` table
   (session, action, before, after, time) so they can be undone and counted.
4. **Effect on evaluation**: Step 17 reports results both **before** and
   **after** user correction, with the number of edits needed per session.

## Open decisions

- **Clips to show.** Options: (a) longest segments — clearest, may all come
  from one part of the meeting; (b) one clip from each third of the meeting —
  shows consistency, may include unclear clips; (c) highest-confidence
  segments (draft).
- **Remember voices across sessions.** Options: (a) never in Phase 5.1 —
  privacy-safe; (b) opt-in per person with explicit consent — convenient;
  (c) designed now, built in Phase 6.5 only. Draft: (c).

## You test this

1. Name the speakers for two tuning meetings. Time how long it takes and how
   many merges or splits you needed.
2. Undo one merge. Do the utterances go back to the original speaker?

## How this number could be lying

- The user knows exactly who spoke in their own recordings; a real user a week
  later may not. Report naming time on a meeting recorded at least a week
  before.
- Results after correction look good by construction; both before and after
  are always reported, with edit counts.

## Verification

- [ ] Naming, merge, split, undo work on the laptop and the Pixel.
- [ ] All edits logged; counts per session available.
- [ ] Summaries and action items show names after naming.
- [ ] Cross-session voice memory not built unless Phase 6.5 is in scope.

## Files changed

- [NEW] `src/conversations/naming.py`, `src/conversations/app_page.py`
- [MODIFY] `src/memories/database.py` (`speaker_edits` table)
- [NEW] `android/.../conversations/NameSpeakersScreen.kt`
- [MODIFY] `README.md`

## Dependencies

- Step 05.

## Common issues

- Merging two clusters that overlap in time is impossible for one person;
  warn the user instead of silently merging.
