# Phase 3.1 Step 04 — Public Dataset Sourcing and Conversion

## What

Find, verify, download (a small, chosen subset only) and convert public
datasets into our own format so they sit next to our recordings and are
scored by the same code:

1. **AMI Meeting Corpus** — real recorded meetings with speaker turns and
   transcripts. Main use: Probe C (speech recognition and speaker separation)
   and Phase 5.1, while our own meetings are still being recorded.
2. **EPIC-KITCHENS-100** — first-person kitchen video with dense, timestamped
   action labels ("pick up cup", "put down knife"). Main use: event
   boundaries for Phase 4, extra pick-up / put-down events for Probe B and
   Phase 4.1.
3. **Ego4D** (subset) — only if the licence agreement is granted in time and
   allows our use. Main use: comparability with published episodic-memory
   work.

Output: `data/scenarios_v1/public/<dataset>/` with converted annotations in
our format, entries in the manifest, rows in the licence ledger, and
converter scripts in `src/scenarios/`.

## Why

- **Our own meetings will take weeks to record.** AMI lets Probe C start
  immediately and gives a second, independent test set: if speaker
  separation works on our meetings but fails on AMI, that is important to
  know.
- **Ground truth we did not write.** Public annotations were made by other
  people. Numbers on them cannot be accused of being tuned to our own
  labelling habits.
- **Comparability.** The panel can be told "on AMI our pipeline gets X",
  which other work also reports on, instead of only numbers on private data.
- **Kitchen activity is exactly the "many short object interactions" case**
  that Phase 4 and Phase 4.1 are built for, with far more labelled events than
  we can annotate ourselves.

## How to implement

1. **Verify before download.** For each dataset, read the licence text
   itself and fill the ledger row (Step 03): what the licence allows, whether
   a registration or agreement is needed, whether results may be published,
   whether derived data may be shown. Planning assumption, all **to be
   verified**: AMI is distributed under a Creative Commons attribution
   licence; EPIC-KITCHENS-100 under a non-commercial Creative Commons
   licence; Ego4D requires a signed licence agreement. A dataset whose row is
   not verified is not downloaded.
2. **Choose subsets, not whole datasets.** Write the selection rules down
   before looking at any results:
   - AMI: about 10 meetings, which gives roughly as much audio as our own
     planned meetings. Prefer meetings with 4 speakers. Use the
     headset-mix or a single distant microphone channel — the distant
     microphone is closer to a phone on a table (see open decision). Fixed
     list of meeting ids recorded in the manifest.
   - EPIC-KITCHENS-100: a handful of videos from 2–3 different participants
     and kitchens, totalling about 1 hour, chosen with a fixed random seed
     from the published splits. Record video ids.
   - Ego4D: only if the agreement is granted; an episodic-memory / natural
     language query subset of about 1 hour.
3. **Download script** `src/scenarios/download.py`: downloads the chosen
   ids only, verifies file sizes or checksums when the source publishes
   them, writes to `MEMORY_SCENARIOS_RAW_DIR/public/<dataset>/`. Resumable.
   Uses the standard library (`urllib`) unless the dataset needs its own
   official download tool, in which case the step documents the exact
   command instead of reimplementing it.
4. **Converters** (one file per dataset, each under 300 lines):
   - `convert_ami.py`: AMI word-level annotations → our speech annotation
     format (Step 09): speaker turns as RTTM (the standard "who spoke when"
     text format: one line per speech segment with start, duration and
     speaker), plus a transcript JSON with words, times and speaker. AMI's
     own topic segmentation and summaries (if present in the release we use)
     are converted to our `meeting_summary` and `action_items` reference
     format; if absent, those categories come only from our own meetings.
   - `convert_epic.py`: EPIC narration and action segments → our event
     annotation format (`events` and `short_events` with verb, noun, start,
     end). Map EPIC verbs to our interaction verbs (`pick_up`, `put_down`,
     `take`, `place`); verbs that do not map are kept with
     `mapped: false`.
5. **Manifest entries.** Each converted item gets a manifest row: `pack`,
   `source` (`public:ami`), `id`, `duration_s`, `media` (audio / video),
   `licence_row` (link to ledger), `split` (`tuning` / `heldout` / `probe`),
   `consent: n/a (public)`.
6. **Sanity reports.** For each dataset, a short report in
   `docs/results/phase-3.1/public-data-report.md`: hours converted, number
   of speakers per meeting, number of pick-up / put-down events, how many
   labels did not map, and 3 example records shown side by side with the
   original annotation.
7. **Keep public and own data apart in results.** Every later result table
   reports public and own data in separate columns. Never mix them into one
   average.

## Open decisions

- **AMI audio channel.** Options: (a) individual headset microphones —
  cleanest, gives an optimistic upper bound; (b) a single distant (table)
  microphone — closest to a phone lying on the table, harder; (c) both, so
  the gap between them is measured. Option (c) costs only extra compute.
- **EPIC-KITCHENS verb mapping.** Options: (a) map only the verbs that
  clearly match ours (take, put) — honest but fewer events; (b) map broadly
  (open, close, move become interactions) — more events, noisier; (c) keep
  EPIC's own verb set for boundary F1 and use only take/put for Probe B.
- **Ego4D at all?** Options: (a) apply now — long lead time, may never be
  used; (b) skip — no comparability with Ego4D-based papers; (c) apply now
  but plan nothing that depends on it. The draft assumes (c).
- **Language.** AMI is English. Our scope is English only (planning default),
  so no Urdu dataset is sourced now. If English plus Urdu becomes a goal, a
  dataset decision is reopened here.

## You test this

1. Open the public data report. Pick one AMI meeting and listen to 2
   minutes of it while reading our converted transcript. Do speaker labels
   and times line up with what you hear?
2. Pick one EPIC video, watch 1 minute, and check 5 converted `short_events`
   against what you see.
3. Run `task scenarios-validate` and confirm the public items pass the same
   validator as our own data.

## How this number could be lying

- Headset audio makes speech recognition look much better than a phone on
  a table will be. Any AMI number says which channel it used.
- EPIC-KITCHENS is filmed with a head-mounted camera by people who know they
  are being recorded, in kitchens only. Results there do not automatically
  transfer to keys in a bag.
- Choosing "nice" meetings or videos by hand would inflate results. The
  selection uses fixed ids chosen by rule or seed before any model is run.

## Verification

- [ ] Ledger rows for AMI, EPIC-KITCHENS-100 and Ego4D filled from the
      actual licence texts, with dates.
- [ ] Only selected ids downloaded; total size recorded.
- [ ] `convert_ami.py` and `convert_epic.py` each under 300 lines, produce
      files that pass `task scenarios-validate`.
- [ ] Public data report written with counts and 3 side-by-side examples per
      dataset.
- [ ] Manifest rows complete, `split` assigned by rule.
- [ ] User spot-checked one AMI meeting and one EPIC video.

## Files changed

- [NEW] `src/scenarios/download.py`, `src/scenarios/convert_ami.py`,
  `src/scenarios/convert_epic.py`
- [NEW] `docs/results/phase-3.1/public-data-report.md`
- [NEW] `data/scenarios_v1/public/...` (git-ignored)
- [MODIFY] `data/scenarios_v1/manifest.json`
- [MODIFY] `docs/results/phase-3.1/licence-ledger.md`
- [MODIFY] `Taskfile.yml` — `scenarios-download`, `scenarios-convert`
- [MODIFY] `README.md`

## Dependencies

- Step 03 (licence ledger, storage layout, raw directory setting).
- Step 09 defines the final annotation formats; this step converts to the
  draft formats and is re-run if Step 09 changes them (converters are cheap
  to re-run).

## Common issues

- Dataset websites change download paths. Record the exact URL and access
  date in the ledger.
- AMI annotations come in a multi-file XML format. Parse with the standard
  library `xml.etree.ElementTree`; no new dependency needed.
- EPIC timestamps are given in different units in different files (frames
  vs time strings). Convert everything to seconds as floats once, in the
  converter.
