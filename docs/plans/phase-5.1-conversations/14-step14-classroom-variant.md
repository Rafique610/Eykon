# Phase 5.1 Step 14 — Classroom Variant and Lecture Questions

## What

Adapt the meeting pipeline to a lecture: one main speaker, a few questions
from listeners, slides or a whiteboard. Tier: **should** (cut before meetings
if time is short; roadmap v2 §7 lists "classroom variant" early in the cut
order).

1. **Session kind `lecture`**: diarization defaults to "main speaker + others"
   (two-cluster prior), "me" detection still on (the user's own questions).
2. **Lecture structure**: topics from Step 08 aligned with slide changes from
   Step 13 (a slide change is a strong topic boundary hint).
3. **Lecture notes**: per slide or topic, the slide text plus the
   extractive (L0) or generative (L2) summary of what was said while that
   slide was shown, with evidence links.
4. **Questions**: `lecture_recall` ("what did the teacher say about
   normalisation?") routed to utterances and slide text in the lecture
   session; "what questions did students ask?" (utterances from non-main
   speakers ending with a question).
5. **Evaluation** on the Phase 3.1 lecture session(s): `lecture_recall`
   accuracy (at least 30 questions), slide-aligned topic boundary F1, notes
   faithfulness (Step 15 audit includes lecture notes).

## Why

- Roadmap v2 defines a lecture as "a meeting with one main speaker plus slides
  or a whiteboard"; reusing the meeting pipeline with small changes is
  cheap.
- Students are an obvious user group for the panel; lecture recall makes the
  daily-life helper concrete.
- Aligning speech with slides is a neat multimodal result (audio + vision
  with a shared timeline) without needing a large model.

## How to implement

1. Session kind and its defaults in `src/conversations/sessions.py`.
2. `src/conversations/lecture.py`: slide–topic alignment, notes builder,
   student-question finder.
3. Router intent `lecture_recall` uses the lecture's utterances and slide
   text, with time windows from slide changes.
4. Notes view on the laptop page and phone screen (slide thumbnail, text,
   summary, play links).

## Open decisions

- **Notes granularity.** Options: (a) per slide — natural for slide lectures;
  (b) per topic — works for whiteboard lectures; (c) per slide when slides
  exist, otherwise per topic (draft).
- **Main-speaker prior.** Options: (a) force two clusters; (b) estimate
  freely; (c) two-cluster prior with an extra cluster allowed if a listener
  talks a lot (draft).

## You test this

1. Open the lecture notes for the recorded lecture. Could you revise from
   them?
2. Ask 5 `lecture_recall` questions and check the quotes and slides shown.

## How this number could be lying

- One or two lecture sessions are a very small sample; results are labelled
  as a case study, not a general claim, unless more lectures are recorded.
- A mock lecture by a classmate is clearer than a real one; record which.

## Verification

- [ ] Lecture sessions processed with the lecture defaults.
- [ ] Notes with slide text, summaries and evidence links.
- [ ] `lecture_recall` accuracy on at least 30 questions (or the shortfall
      stated).
- [ ] Slide-aligned topic boundary F1 reported.

## Files changed

- [NEW] `src/conversations/lecture.py`
- [MODIFY] `src/conversations/sessions.py`, `src/memories/router.py`,
  `src/conversations/app_page.py`
- [NEW] `android/.../conversations/LectureNotesScreen.kt`
- [NEW] `docs/results/phase-5.1/step14-classroom.md`
- [MODIFY] `README.md`

## Dependencies

- Steps 12, 13.

## Common issues

- Lecturer walking away from the phone: audio level drops, ASR worse in those
  parts; mark low-energy segments and report WER separately.
