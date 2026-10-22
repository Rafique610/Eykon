# Phase 6 Step 07 — Privacy Controls in the Loop

## What

Privacy features that work **while recording**, not only as settings:

1. **Pause** from the notification, the app, and (if feasible) a quick
   gesture; resume the same way; paused periods are not recorded at all.
2. **Exclusion places**: the user marks places (from Phase 4.1 Step 08 place
   clusters) as "never record here" (bathroom, bedroom); when the current
   frame matches an excluded place, capture pauses automatically.
3. **Exclusion times**: schedules ("never between 10 pm and 7 am").
4. **Sensitive content guard**: frames dominated by a screen with text or a
   document (OCR finds many words) can be stored as text-only without the
   thumbnail, if the user enables it.
5. **Retention settings**: how long thumbnails, audio and transcripts are
   kept (Phase 5 Step 10 lifecycle), shown in plain language.
6. **Delete**: delete the last N minutes, a whole day, a session, or
   everything; deletion is explicit (core.md: no silent destructive actions)
   and confirmed.
7. **Bystanders**: no face storage or recognition in this phase (Phase 6.5 is
   opt-in, stretch); conversations recorded only as sessions with the consent
   reminder.

## Why

- Roadmap §3: privacy controls in the loop are part of our delta over
  LightMem-Ego (which has no privacy pipeline). This step makes that claim
  real.
- A wearable memory device raises obvious privacy concerns at a defense; a
  live demo of "pause", "never record here" and "delete last 10 minutes" is
  the most convincing answer.

## How to implement

1. Pause / resume through `CaptureService` (Step 02) with state persisted.
2. Exclusion places: place embedding match each N seconds (cheap, reuses the
   shared encoder); on match above threshold → pause and show "paused: private
   place". False pauses and misses measured on field days.
3. Exclusion schedules: simple time rules in settings.
4. Sensitive content guard: reuse OCR (Phase 5.1 Step 13) word count as the
   trigger; only when enabled.
5. Deletion: functions in the memory layer that delete rows, files, index
   entries and ledger rows derived only from deleted data; a deletion log
   (what, when — not the content).
6. Privacy screen explaining in plain words what is stored, where, and for
   how long.

## Open decisions

- **Ledger rows after deleting their evidence.** Options: (a) delete them
  too — consistent, "where are my keys" may lose its answer; (b) keep the
  state without evidence, marked "evidence deleted" — useful, less
  transparent; (c) ask the user at deletion time. Draft: (c) with (a) as
  default.
- **Exclusion place failure mode.** Options: (a) pause when unsure (privacy
  first); (b) record when unsure (memory first); (c) user setting. Draft: (a).

## You test this

1. Mark your bathroom as excluded; walk in and out with recording on. Does it
   pause and resume?
2. Delete the last 10 minutes after a short session; ask about something from
   those minutes. It must not be found.
3. Read the privacy screen as if you were a panel member.

## How this number could be lying

- Exclusion-place accuracy on your own home after you marked it is optimistic;
  test a second excluded place marked on a different day.

## Verification

- [ ] Pause, exclusion places, exclusion times, sensitive content guard,
      retention, deletion all work on both phones.
- [ ] Deleted data not retrievable by search, ledger or answers (tested).
- [ ] Exclusion place false pause / miss rates measured in Step 13.
- [ ] Privacy screen written in plain language.

## Files changed

- [NEW] `android/.../privacy/` (controls, screens), deletion functions in
  memory packages
- [MODIFY] `src/memories/` deletion helpers (laptop parity)
- [NEW] `docs/results/phase-6/step07-privacy.md`
- [MODIFY] `README.md`

## Dependencies

- Step 03; Phase 4.1 Step 08 (places) if in scope (otherwise exclusion places
  use the Phase 4 Tier 1 embeddings).

## Common issues

- Deleting from FTS indexes and embeddings tables is easy to forget; the
  deletion test searches every index.
