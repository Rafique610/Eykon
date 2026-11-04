# Phase 3.1 Step 03 — Data Governance: Consent, Licences, Privacy, Storage

## What

Set up the rules and files that make it safe and legal to collect, keep and
use the data in this phase:

1. **Consent**: a one-page plain-language consent form for anyone recorded
   (meetings, lecture, conversations at home), and a consent register.
2. **Licence ledger**: one table listing every external dataset and every
   model we plan to use, with its licence, what it allows, where we checked
   it and when.
3. **Privacy rules**: what is never recorded, how bystanders are handled,
   retention and deletion.
4. **Storage layout and budget**: where raw media lives, what is git-ignored,
   how much disk each pack needs, backups.
5. **Fix the `.gitignore` bug** found while planning: `data/` (no leading
   slash) ignores every folder named `data`, including the Android Room
   package.

## Why

- Meetings and lectures record other people's voices. Recording without
  consent is unethical, likely against university policy, and would make the
  data unusable in a thesis.
- The panel is strict. A slide that says "all recordings consented, consent
  forms on file, no data leaves the device" closes a line of attack before it
  opens.
- Licences matter twice: for **datasets** (some allow research only, some
  forbid redistribution) and for **models we ship in the app** (some popular
  detector releases are AGPL — using them in an app has obligations; the
  handoff doc flags this explicitly).
- Video is big. Several hours of 1080p video plus copies of extracted frames
  can fill a laptop disk in the middle of an experiment.
- The `.gitignore` bug means the Android database code is not in version
  control. Every later Android step depends on it.

## How to implement

1. **Consent form** `docs/results/phase-3.1/consent-form.md` (printable).
   Plain language, one page:
   - what is recorded (audio, video, or both), for how long,
   - purpose: a final-year project on on-device memory; data stays on the
     student's own devices, is never uploaded, never published as raw media,
   - what appears in the thesis: only aggregate numbers and, if separately
     agreed, short anonymised quotes; no faces or voices published,
   - right to withdraw at any time, and what happens then (their session is
     deleted, results recomputed without it),
   - tick boxes: audio yes/no, video yes/no, face visible yes/no, quotes in
     thesis yes/no,
   - signature and date.
2. **Consent register** `data/scenarios_v1/consent/register.csv` (git-ignored):
   `participant_code, session_ids, audio, video, face, quotes, date, withdrawn`.
   Use participant codes (P01, P02…) everywhere else; real names only in the
   register and on the signed forms.
3. **Ask about university rules.** Write a short message to the supervisor
   asking whether the department requires ethics approval for recording
   classmates in mock meetings and a lecture. Record the answer in the
   ledger. Do not record a real lecture without the lecturer's consent and
   the department's answer.
4. **Licence ledger** `docs/results/phase-3.1/licence-ledger.md`, one row per
   item, columns: `item, kind (dataset/model/library), licence as stated,
   source URL checked, date checked, allows research use?, allows shipping in
   an app?, attribution needed?, notes`. First rows to fill (each "to be
   verified" until someone reads the actual licence page):
   - Datasets: AMI Meeting Corpus, EPIC-KITCHENS-100, Ego4D.
   - Models already used: Gemma 4 E2B (LiteRT-LM), bge-small-en-v1.5,
     ms-marco-MiniLM-L-6-v2 cross-encoder, Whisper models used by
     `WhisperTranscriber.kt`, Moondream2, PaliGemma.
   - Candidates for Steps 17 and 20 are added there.
   Rule: nothing goes into the app or into a reported experiment until its
   row says "verified".
5. **Privacy rules** `docs/results/phase-3.1/privacy-rules.md`:
   - never record bathrooms, people who have not consented, screens with
     other people's private messages, bank cards or ID documents (the
     "passport" scenario uses an expired passport or a printed mock-up);
   - if a non-consenting person enters the frame or starts talking, stop
     or mark the time range `exclude` in the annotation; excluded ranges are
     cut before any processing;
   - retention: raw media kept until the end of the project plus whatever
     period the university requires, then deleted; record the deletion date
     in the register;
   - YouTube: not used until the department confirms (planning default,
     07 October 2026).
6. **Storage layout and budget.**
   - Raw originals: an external drive or a separate folder outside the repo,
     path configured through a new setting `MEMORY_SCENARIOS_RAW_DIR`
     (Pydantic settings, `src/config.py`, never an environment variable read
     directly).
   - Working copies (extracted frames, audio WAVs, annotations):
     `data/scenarios_v1/` inside the repo, git-ignored.
   - Committed: only manifests without personal data, annotation schemas,
     result reports (`docs/results/phase-3.1/`).
   - Budget estimate per pack, to be replaced by measured sizes after
     Step 07: objects/daily life (at least 3 h video), meetings (about 10 ×
     30 min audio + optional video), lecture (at least 1 × 45–60 min), public
     AMI subset. Measure the size of one 10-minute test recording in Step 06
     and multiply; do not guess.
   - Backup: one copy of raw originals on a second disk; annotation files
     are small and backed up after every annotation session.
7. **Fix `.gitignore`.** Change `data/` to `/data/` so only the top-level
   data folder is ignored. Then check with `git status` (once the repo is a
   git repository) that `android/app/src/main/java/com/eykon/memory/data/`
   would be tracked. The Android `data/` package (`MemoryDatabase`,
   `MemoryDao`, `MemoryRecord`) is missing from this copy; the user has it
   locally (confirmed 07 October 2026) and copies it back after this fix.

## Open decisions

- **Ethics approval route.** Options: (a) supervisor confirms that signed
  consent forms are enough — fastest; (b) formal departmental ethics
  approval — slowest (could take weeks), but strongest for the panel;
  (c) record only the student and family at home until approval arrives,
  meetings later — keeps the objects pack moving. Depends on the
  supervisor's answer.
- **Where raw media lives.** Options: (a) external drive — safe from laptop
  disk filling, but experiments must have the drive attached; (b) laptop
  disk with a strict budget — always available, risk of filling up;
  (c) originals on the drive, extracted frames and WAVs on the laptop —
  middle ground, the draft above assumes this.
- **Anonymising stored meeting audio.** Options: (a) keep raw audio, names
  only in the register — simplest, needed for re-running ASR; (b) keep only
  transcripts after Step 11 — less sensitive, but Probe C and Phase 5.1
  cannot be re-run; (c) keep raw audio until Phase 5.1 ends, then delete —
  middle ground.

## You test this

1. Read the consent form as if you were a classmate being asked to sign it.
   Is anything unclear or worrying? Change the wording until you would sign
   it yourself.
2. Send the ethics question to your supervisor (I will draft the message;
   you send it) and paste the reply into the ledger.
3. Open the licence ledger and check two rows yourself against the real
   licence pages: AMI and one model. Do they match what is written?
4. After the `.gitignore` change, run `git check-ignore -v android/app/src/main/java/com/eykon/memory/data/MemoryDao.kt`.
   It should print nothing (meaning: not ignored).

## How this number could be lying

- The storage budget is an estimate until Step 06 measures a real
  recording. Mark it "estimated" until then.
- A licence ledger row copied from a blog or a model card summary may be
  wrong. A row only counts as verified if the source column points to the
  licence text itself.

## Verification

- [ ] Consent form written and reviewed by the user.
- [ ] Consent register created, git-ignored, with participant codes only
      outside it.
- [ ] Supervisor asked about ethics; answer recorded.
- [ ] Licence ledger has rows for all datasets and models listed above;
      each marked verified or "to be verified" with a date.
- [ ] Privacy rules written, including the exclude-range rule.
- [ ] `MEMORY_SCENARIOS_RAW_DIR` setting added; `task check-config` shows it.
- [ ] `.gitignore` uses `/data/`; the Android `data/` package is no longer
      ignored (`git check-ignore` returns nothing).
- [ ] User informed about the missing Android `data/` package.

## Files changed

- [NEW] `docs/results/phase-3.1/consent-form.md`
- [NEW] `docs/results/phase-3.1/licence-ledger.md`
- [NEW] `docs/results/phase-3.1/privacy-rules.md`
- [NEW] `data/scenarios_v1/consent/register.csv` (git-ignored)
- [MODIFY] `.gitignore` — `data/` becomes `/data/`; add `/data/scenarios_v1/`
  explicitly for clarity
- [MODIFY] `src/config.py` — `scenarios_raw_dir` setting
- [MODIFY] `.env.example` — `MEMORY_SCENARIOS_RAW_DIR=`
- [MODIFY] `README.md` — data and privacy section

## Dependencies

- None. Can run in parallel with Steps 01–02.

## Common issues

- Participants agree verbally but forget to sign. No signature, no
  recording.
- One participant withdraws after annotation is done. Keep the processing
  scripted so their session can be removed and all numbers recomputed with
  one command.
- `/data/` in `.gitignore` stops ignoring other nested `data` folders that
  were meant to be ignored (for example a `data/` under `scratch/`). Check
  `git status` for newly visible large files before the next commit.
