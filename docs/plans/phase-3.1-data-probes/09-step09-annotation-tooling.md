# Phase 3.1 Step 09 — Annotation Tooling and File Formats

## What

Choose (or build) the annotation tool, and fix the file formats every
annotation is stored in, with a validator and converters:

1. **Formats** (final versions of the drafts used in Step 04):
   - `annotations.json` per Pack A session: `events` (coarse activity
     segments), `short_events` (pick up, put down… with object, from, to),
     `state_changes` (entity, attribute, old value, new value, time),
     `speech_gist` (time, speaker code, short gist — for
     `conversation_recall`), `exclude` ranges, `visibility` flags (was the
     move actually visible on camera).
   - Meetings / lecture: `turns.rttm` (who spoke when — the standard
     diarization text format), `transcript.json` (words or sentences with
     start, end, speaker code), `summary_ref.json` (reference summary
     bullets, each with supporting time ranges), `actions_ref.json`
     (reference action items: owner, text, time agreed), `slides.json`
     (lecture only: slide change times and slide text).
   - `labels/` for probe labels (Step 14 writes those).
2. **Validator** `src/scenarios/annotations.py`: loads each format into
   dataclasses and returns problems (times inside session length, start
   before end, objects and places from the session vocabulary, speaker codes
   from the manifest participants, no overlap with `exclude` ranges).
3. **Tool**: the chosen annotation tool (open decision) plus import/export
   so that whatever the tool saves is converted to the formats above.
4. **Annotation guide** `docs/results/phase-3.1/annotation-guide.md`: rules
   for when an event starts and ends, what counts as a "move", how to mark an
   object that is only partly visible, how to mark overlapping speech, and
   how to write a reference summary bullet.

## Why

- Every later number is computed against these files. A clear format with a
  validator stops silent mistakes (a move timed after the session ended, a
  place spelled two ways).
- Speaker annotation in a standard format (RTTM) lets us use standard
  scoring tools for diarization error instead of writing our own.
- Annotation is the slowest human task in the project. The right tool can
  make it several times faster; the wrong one can stall the phase.
- The annotation guide is what makes two annotators agree. Without written
  rules, inter-annotator agreement (Step 10) will be low for reasons that
  have nothing to do with the system.

## How to implement

1. **Write the formats** as dataclasses in `src/scenarios/annotations.py`
   (standard library; split into `annotations_objects.py` and
   `annotations_speech.py` if one file goes over 300 lines).
2. **Fill a small example** for each format by hand from the Step 05 pilot
   sessions; the validator must accept them.
3. **Pick and set up the tool** (see open decisions). Requirements, in
   order: works offline on the laptop, shows video and audio waveform with
   a timeline, allows labelled time ranges and point events, exports
   something we can convert, is quick for one person.
4. **Speed trick for Pack A**: since moves are announced out loud, run a
   quick speech-to-text pass over the session audio (no laptop speech
   recogniser is installed yet; the runtime comes from the Step 20
   shortlist, and adding it as a dependency needs the user's approval —
   until then, annotation is fully manual)
   and pre-fill draft `short_events` from phrases like "keys into bag". The
   annotator then only confirms or corrects times and fills `visibility`.
   Pre-filled entries are marked `prefilled: true` until a human confirms
   them; unconfirmed entries are rejected by the validator.
5. **Speed trick for meetings**: pre-fill `transcript.json` with a speech
   recognition pass and the RTTM with a diarization pass, then correct by
   hand. Important: the model used for pre-filling must **not** be the same
   system evaluated in Probe C, or the reference is biased towards it (see
   "How this number could be lying").
6. **Annotation guide**: one page per pack, with 3 worked examples each
   taken from the pilots.
7. **Time tracking**: the tool or a simple sheet records annotation minutes
   per session, so the real cost of annotation is known (and reportable).

## Open decisions

- **Annotation tool** (inherited from old Phase 4 Step 01, extended to
  audio). Options:
  (a) **ELAN** — built for time-aligned video and audio annotation,
  light, offline, exports XML we convert; learning curve of a few hours;
  (b) **CVAT** (local Docker) — strong for boxes on frames, weaker for audio
  timelines, heavy setup;
  (c) **Label Studio** (local) — handles video, audio and text in one tool,
  medium setup, exports JSON;
  (d) **a small Streamlit page in our app** — no new tools, matches the
  stack, but we must build timeline and waveform features ourselves.
  Licences of the chosen tool go into the ledger. A short trial (30 minutes
  each on the pilot session) for the top two is the cheapest way to decide.
- **Reference transcripts for meetings.** Options: (a) fully manual
  transcription — unbiased, about 4–6× real time; (b) machine pre-fill with a
  different, larger model than the one being evaluated, then manual
  correction — faster, small bias risk; (c) manual transcription only for
  the segments used in questions — cheapest, but WER can then only be
  measured on those segments.
- **Bounding boxes for objects.** Options: (a) none — moves and times only,
  much faster; (b) boxes on a sample of frames for Probe A only — enables
  size and location analysis where it matters; (c) boxes everywhere — slow,
  probably unnecessary. The draft assumes (b), done inside Step 14's
  labelling kit rather than in the general tool.

## You test this

1. Annotate 5 minutes of the pilot Pack A session with the chosen tool. Time
   yourself.
2. Annotate 5 minutes of the pilot meeting (speaker turns plus transcript
   correction). Time yourself.
3. Run `task annotations-validate -- <session>` and fix whatever it reports.
4. Tell me which rule in the annotation guide was unclear while you were
   doing it.

## How this number could be lying

- Machine pre-fill biases the reference toward the pre-fill model. If that
  model is also evaluated, its error looks smaller than it is. The pre-fill
  model is recorded in the annotation metadata and excluded from the systems
  under test, or the bias is reported.
- Fast tools encourage sloppy boundaries. Agreement in Step 10 shows how
  precise the boundaries really are.
- Annotation minutes per hour measured on pilots will underestimate the cost
  of hard sessions (overlapping speech). Track minutes on every session.

## Verification

- [ ] All formats defined as dataclasses with a validator; files under 300
      lines each.
- [ ] Hand-written examples for every format pass the validator; 5 broken
      examples fail with clear messages.
- [ ] Tool chosen (trial notes recorded) and installed; licence in the ledger.
- [ ] Import from the tool's export into our formats works on the pilots.
- [ ] Pre-fill scripts produce `prefilled: true` drafts that the validator
      rejects until confirmed.
- [ ] Annotation guide with worked examples written.
- [ ] Annotation speed measured on the pilots (minutes per minute of media).

## Files changed

- [NEW] `src/scenarios/annotations.py` (split into `annotations_objects.py`
  and `annotations_speech.py` if needed)
- [NEW] `src/scenarios/import_<tool>.py`, `src/scenarios/prefill.py`
- [NEW] `docs/results/phase-3.1/annotation-guide.md`
- [MODIFY] `docs/results/phase-3.1/licence-ledger.md`
- [MODIFY] `Taskfile.yml` — `annotations-validate`, `annotations-prefill`
- [MODIFY] `README.md`

## Dependencies

- Step 01 (categories and sub-tags), Step 02 (slot vocabulary: verbs, size
  classes), Step 05 pilots (example material).

## Common issues

- Tools export times in milliseconds, frames or `hh:mm:ss.ms` strings.
  Normalise to float seconds in the importer only.
- RTTM requires speaker names without spaces; use participant codes (P01).
- Pre-fill transcripts in noisy meetings are poor; correcting them may be
  slower than typing. Measure on one noisy pilot before relying on it.
