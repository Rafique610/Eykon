# Phase 5.1 Step 07 — Aligned Transcript Builder (Overlap Aware)

## What

Combine the ASR output (Step 03) and the speaker labels (Steps 04–06) into
one clean, aligned transcript stored as `utterances`:

- each utterance: session, speaker id, start, end, text, ASR confidence,
  speaker confidence, flags (`overlap_suspected`, `low_confidence`),
- words assigned to speakers by time (word-level times where available),
  splitting an ASR segment when the speaker changes inside it,
- consecutive utterances from the same speaker merged up to a maximum length,
- an embedding and full-text index entry per utterance (Phase 1 embedder,
  existing FTS), so conversation search works like the rest of memory,
- a readable transcript view (laptop page, phone screen) with speaker
  colours, times and click-to-play.

## Why

- `who_said` and `conversation_recall` need text with speaker and time in
  the same row; summaries and action items (Steps 09–10) need clean speaker
  turns as input.
- Overlapping speech is common in real meetings; forcing it into one speaker
  silently creates wrong attributions. Flags let answers say so.
- Indexing utterances with the existing embedder and FTS reuses the Phase 1
  retrieval that already scored Hit@5 93.33 % on text, instead of building a
  new search.

## How to implement

1. `src/conversations/align.py`: `build_utterances(asr_segments,
   speaker_windows) -> list[Utterance]`.
2. Word-to-speaker assignment by maximum time overlap; if no word times,
   split segments proportionally and mark `approx_times`.
3. Merge rule: same speaker, gap under a threshold, total length under a
   maximum (so evidence links stay precise).
4. Overlap: if two speakers are active in the same span (from diarization
   flags), keep the utterance with both candidates and `overlap_suspected`.
5. Indexing via existing `src/memories/` functions (Ponytail: reuse) with
   `source_type="utterance"` and metadata pointing to the session.
6. Evaluation: speaker-attributed word error rate (words with the wrong
   speaker count as errors, a simplified version of the standard
   "concatenated minimum-permutation" metric) per condition.

## Open decisions

- **Maximum utterance length.** Options: (a) 15 s — precise evidence, many
  rows; (b) 30 s (draft); (c) whole speaker turn — natural, long turns make
  evidence vague.
- **Overlap representation.** Options: (a) duplicate the text for both
  candidate speakers — easy to query, double counting; (b) one row with two
  candidate speakers (draft); (c) drop overlap text — loses content.

## You test this

1. Open the transcript view for a tuning meeting and read 5 minutes with the
   audio. Are the speaker changes in the right places?
2. Search "deadline" across your sessions. Do the right utterances appear
   with speaker and time?

## How this number could be lying

- Speaker-attributed WER combines two error sources; report it next to plain
  WER and DER so the reader can see which part fails.
- Approximate times (no word timestamps) can look precise in the UI; they are
  marked.

## Verification

- [ ] Utterances built for all tuning meetings; flags set where appropriate.
- [ ] Indexed and searchable through existing memory search.
- [ ] Speaker-attributed WER per condition reported.
- [ ] Transcript view works on laptop and Pixel.

## Files changed

- [NEW] `src/conversations/align.py`
- [MODIFY] `src/memories/service.py` (index utterances), `src/conversations/app_page.py`
- [NEW] `android/.../conversations/TranscriptScreen.kt`
- [MODIFY] `README.md`

## Dependencies

- Steps 03, 05 (and 04, 06).

## Common issues

- FTS on Android: FTS5 may not be available (roadmap §8); utterance search
  must work with whatever Phase 5 decided.
