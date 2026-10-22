# Phase 3.1 Step 11 — Annotation Pass: Meetings and Lecture

## What

Produce the ground truth for conversations, for all tuning meetings, the
lecture, and the converted AMI subset (where AMI does not already provide
it):

- `turns.rttm` — who spoke when, including overlapping speech,
- `transcript.json` — corrected words or sentences with speaker codes and
  times,
- `summary_ref.json` — a reference summary of 5–10 bullets per meeting,
  each bullet with the time ranges that support it,
- `actions_ref.json` — reference action items (owner, task, time agreed),
  cross-checked against the paper list written at the end of the meeting,
- `topics.json` — topic segments (start, end, short title), used later for
  topic splitting in Phase 5.1,
- lecture only: `slides.json` — slide change times and slide text.

Plus agreement: one meeting summarised and action-itemised by two people
independently.

## Why

- Probe C measures speech recognition error (WER: the share of words wrong,
  missing or extra) and diarization error (DER: the share of time assigned
  to the wrong speaker, missed or falsely detected). Both need a corrected
  transcript and speaker turns as the reference.
- `meeting_summary` and `action_items` questions (Step 01) are judged
  against references. A reference summary written by one person is one
  opinion; the second person's version shows how much honest summaries
  differ, which is the fair ceiling for any system.
- Topic segments let Phase 5.1 evaluate topic splitting without a new
  annotation pass.

## How to implement

1. **Order**: the two meetings Probe C will use first (one clean, one
   noisy, chosen by fixed rule from the condition matrix), then the rest,
   then the lecture.
2. **Speaker turns**: start from a pre-fill diarization (Step 09, with a
   model not under test) or from scratch; correct in the tool. Overlaps are
   kept as overlapping RTTM lines, not forced into one speaker. Very short
   back-channel sounds ("mm", "yeah") under 0.5 s are marked with a
   `backchannel` flag so they can be excluded consistently (rule in the
   guide).
3. **Transcript**: corrected text per turn. Rules in the guide: spelling of
   names and project terms, how to write numbers, what to do with
   unintelligible words (`[unclear]`, excluded from WER).
4. **Reference summary**: written **after** listening, from the
   transcript, without looking at any system output. Each bullet must
   point to at least one supporting time range. 5–10 bullets for a
   30-minute meeting.
5. **Action items**: from the transcript, then compared with the paper list;
   differences are resolved by listening, and the paper list is kept as a
   second reference.
6. **Topics**: segment boundaries where the agenda item changes, with a
   short title.
7. **Lecture**: slide change times from notes or video; slide text from the
   slides file if provided, otherwise typed from the frames.
8. **Agreement**: second person (or user a week later) writes summary bullets
   and action items for one meeting. Measure action item overlap (precision
   and recall of B against A) and bullet overlap judged by a third look
   (same fact / different fact). Output:
   `docs/results/phase-3.1/agreement-meetings.md`.

## Open decisions

- **Reference transcript method**: inherited from Step 09 (fully manual /
  pre-fill then correct / manual only on question segments).
- **AMI references**: options: (a) use AMI's own annotations as-is (where
  present) — independent ground truth, but their summary style may differ
  from ours; (b) write our own summaries for the AMI subset — consistent
  style, more work; (c) use AMI annotations for WER and DER only, and our
  own summaries for summary evaluation on our meetings only. The draft
  leans towards (c).
- **Summary length rule**: options: (a) fixed 5–10 bullets — comparable
  across meetings; (b) length proportional to content — more natural,
  harder to compare; (c) fixed bullets plus an optional "details" list.

## You test this

1. Correct the transcript for 5 minutes of the noisy meeting. How many
   corrections per minute did you make? (This roughly shows how bad the
   pre-fill was.)
2. Write the reference summary for one meeting without looking at anything
   but the transcript. Then compare it with the paper action items. What
   did you leave out?
3. Read the meeting agreement report. Would you accept the other person's
   summary as correct?

## How this number could be lying

- References written from a machine pre-fill inherit its mistakes in places
  nobody checked closely. The time spent correcting each meeting is logged;
  a suspiciously fast correction is re-checked.
- The user wrote the meeting scenario sheets with planted facts, so the
  reference summary may over-weight planted facts. Bullets are tagged
  `planted: true/false`.
- Agreement on one meeting is a small sample. Reported as such.

## Verification

- [ ] All tuning meetings and the lecture have RTTM, transcript, summary,
      action items and topics; all validate.
- [ ] AMI subset has RTTM and transcript in our format (from Step 04), plus
      whatever summary decision was taken.
- [ ] The two Probe C meetings were annotated first.
- [ ] Agreement report for one meeting written.
- [ ] Held-out meetings untouched.

## Files changed

- [NEW] `data/scenarios_v1/meetings/<session>/{turns.rttm, transcript.json,
  summary_ref.json, actions_ref.json, topics.json}` (git-ignored)
- [NEW] `data/scenarios_v1/lecture/<session>/slides.json` (git-ignored)
- [NEW] `docs/results/phase-3.1/agreement-meetings.md`
- [MODIFY] `src/scenarios/agreement.py` — action item and summary overlap
- [MODIFY] `docs/results/phase-3.1/data-status.md` (generated)
- [MODIFY] `README.md`

## Dependencies

- Step 04 (AMI conversion), Step 08 (recordings), Step 09 (tool, formats,
  guide).

## Common issues

- Overlapping speech is the slowest part to annotate. Annotate overlap only
  where it lasts over 0.5 s; shorter overlaps are noted as a count.
- Speakers with similar voices get swapped during correction. Check speaker
  codes against the video (if recorded) or seat order notes.
- Long meetings make summaries drift toward the end. Summarise per topic
  first, then merge.
