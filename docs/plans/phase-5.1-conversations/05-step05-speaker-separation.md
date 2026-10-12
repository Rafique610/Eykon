# Phase 5.1 Step 05 — Speaker Separation for Others (Diarization)

## What

Group the other people's speech into speakers ("speaker 1, 2, 3"), as well as
the evidence allows:

1. speaker embeddings per speech segment (or per 1.5 s window inside long
   segments, so a turn change inside a segment can be found),
2. the user's segments fixed as `me` from Step 04,
3. clustering of the remaining windows into speakers — with the number of
   speakers given by the user at session start (if provided) or estimated,
4. smoothing: very short speaker switches merged into the surrounding speaker
   unless strongly supported,
5. output: `diarization.rttm` per session and `speaker_id` on each window,
   with a per-window confidence (distance to its cluster centre vs the next
   nearest),
6. evaluation: DER and its parts, overlap DER, speaker count error, per
   condition, on tuning meetings and AMI.

Only built at the scope Probe C allows (overview scope rule). At "unusable"
scope this step is reduced to measuring and documenting why.

## Why

- `who_said` questions and per-speaker summaries need speaker labels.
- Speaker separation is the least reliable part of the phone pipeline;
  confidence per window lets later steps say "probably speaker 2" instead of
  stating a guess as fact.
- Separating "me" first (Step 04) and clustering the rest is simpler and more
  robust than clustering everyone, and keeps the most useful speaker right.

## How to implement

1. `src/conversations/diarize.py`, using `src/speech/speakers.py` for
   embeddings; clustering written with numpy (agglomerative clustering with
   cosine distance and a stopping threshold, or k-means when the count is
   known) — no new dependency unless approved.
2. Windowing parameters, threshold and smoothing in settings; tuned on the
   pilot meeting and one AMI meeting **not** in the evaluation set.
3. Known-count vs estimated-count both supported; the session's
   `expected_speakers` decides.
4. Overlap: windows with high energy and low similarity to any single
   cluster are flagged `overlap_suspected` instead of being forced into one
   speaker.
5. Scoring with the Phase 3.1 DER implementation (`src/probes/speech_metrics.py`,
   moved to `src/speech/metrics.py` if shared).
6. Android: the same logic in the processing worker; embeddings via the same
   model file.

## Open decisions

- **Diarization approach**: inherited from Phase 3.1 Step 20 ((a) own
  embeddings + clustering, (b) packaged pipeline, (c) laptop-only upper bound
  plus (a) on the phone). Draft follows the Step 20 choice.
- **Window length.** Options: (a) 1.0 s — finds quick turns, noisier
  embeddings; (b) 1.5 s (draft); (c) 3.0 s — stable, misses short replies.
- **Ask for the number of speakers?** Options: (a) always ask — most
  accurate, small UX cost; (b) never ask — automatic; (c) optional field,
  estimated when empty (draft).

## You test this

1. Look at the speaker timeline for one clean and one noisy tuning meeting
   (coloured bars, play on click). Where does it get confused?
2. Count how often two participants are merged into one speaker, and how
   often one participant is split into two.

## How this number could be lying

- Tuning the clustering threshold on evaluation meetings would inflate
  results; tuning uses only the pilot and one excluded AMI meeting.
- DER with a 0.25 s collar forgives boundary errors; also report DER without
  collar for comparison.
- Meetings with the same participants share voices across sessions; report
  per participant set.

## Verification

- [ ] RTTM and per-window confidence produced for all tuning meetings and the
      AMI subset.
- [ ] DER (with and without collar), its parts, overlap DER and speaker count
      error per condition, with per-meeting rows.
- [ ] Known-count vs estimated-count compared.
- [ ] Tuning data separate from evaluation data (listed).

## Files changed

- [NEW] `src/conversations/diarize.py`
- [MODIFY] `src/speech/speakers.py`, `src/config.py`
- [NEW] `docs/results/phase-5.1/step05-diarization.md`
- [MODIFY] `Taskfile.yml` (`session-diarize`), `README.md`

## Dependencies

- Step 03 (segments), Step 04 (`me` labels).

## Common issues

- Agglomerative clustering on thousands of windows is slow in pure numpy;
  cluster segment-level embeddings first, then refine windows inside
  segments.
- Laughter, coughs and background TV form their own "speaker"; drop clusters
  with very little total speech, and report how often that happens.
