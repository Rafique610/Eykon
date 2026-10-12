# Phase 3.1 Step 13 — Probe Pre-Registration

## What

Before any probe produces a single output, write down and commit, for each
of Probes A, B and C:

- the exact question the probe answers,
- the hypothesis (what we expect) and the null result (what "no" looks like),
- the data used (which sessions, how many frames, events or minutes, how
  they are sampled),
- who labels, and whether labelling is blind,
- the metrics and how they are computed,
- the **unacceptable result**, fixed now, and the "acceptable" and "unclear"
  zones,
- the decision each outcome leads to (Gate 1 table),
- how uncertainty is reported (confidence intervals).

Output: `docs/results/phase-3.1/preregistration.md`, committed before Step 15,
Step 19 and Step 21 run. The commit date proves the order (the repo becomes
a git repository first, if it is not one yet — this copy is not).

## Why

- If the threshold is chosen after seeing the result, any result can be
  made to look acceptable. The panel's question "do you really need an
  LLM?" deserves an answer that was not shaped by what we hoped.
- Writing the decision table first forces each probe to actually decide
  something. A probe that cannot change any plan is not worth running.
- Sample sizes chosen in advance stop "run until it looks good".
- This is the practice the roadmap calls "probes before commitments" and
  "honest measurement" (v2 §2, principles 5 and 6).

## How to implement

1. **Uncertainty method, one for all probes.** Rates (invention rate, miss
   rate, precision, recall) get a 95 % Wilson score interval — a standard
   way to put error bars on a percentage that behaves well with small
   samples. One small function in `src/probes/common.py` (standard library
   `math` only). Rule of thumb for planning: with about 100 items, a rate
   near 50 % has an interval of roughly ±10 percentage points; near 10 % it
   is narrower. This is why "about 100 frames" is the minimum, not a target.
2. **Probe A (VLM invention and misses)** — draft for the user to confirm:
   - Question: on frames from our own egocentric recordings, how often does
     the small VLM mention an object that is not there (invention), and how
     often does it fail to mention a vocabulary object that is clearly
     visible (miss)?
   - Data: at least 120 frames, stratified by object size (small / medium /
     large) × lighting (bright-normal / dim), at least 20 frames per cell,
     sampled by script with a fixed seed from tuning sessions (Step 14).
   - Models: Gemma 4 E2B (primary, LiteRT-LM) with both the Phase 3 free
     caption prompt and the Step 02 slot prompt. Other VLMs only if already
     installed (Moondream2, PaliGemma from Phase 3).
   - Labels: human, blind to which model and prompt produced the output.
   - Metrics: invention rate = invented object mentions / all object
     mentions; miss rate = visible vocabulary objects not mentioned / all
     visible vocabulary objects; both per size × lighting cell; plus JSON
     parse failure rate for the slot prompt.
   - **Unacceptable (draft): invention rate above 10 % overall, or miss rate
     above 40 % for small objects**, judged on the upper end of the 95 %
     interval for invention and the point estimate for misses. These numbers
     are proposals; the user fixes them in this step (see Open decisions).
3. **Probe B (cheap path vs VLM on pick-up / put-down)** — draft:
   - Question: does the cheap path (hand landmarks + hand-centred crop +
     image-text matching against the object vocabulary, no language model)
     detect pick-up and put-down events with object identity at least as
     well as the VLM path, at a fraction of the cost?
   - Data: the 10-minute keys recording **plus all other state-change script
     sessions**, so that there are at least 30 annotated visible events (the
     keys recording alone will likely have only about 10–20 moves; the
     pessimist rule needs 30). Results are reported for the keys recording
     alone and for all scripts.
   - Metrics: event precision and recall (an event counts as correct if
     object and verb match and the time is within ±2 s — tolerance revisited
     after Step 10 agreement), object identity accuracy among detected
     events, cost per minute of video (latency, peak RAM, model calls).
   - **Viable (draft): cheap path recall within 10 percentage points of the
     VLM path or better, at less than a quarter of its compute per minute.
     Not viable: recall below 50 % on visible events.**
4. **Probe C (speech and speakers)** — draft:
   - Question: on phone-recorded 30-minute meetings, is speech recognition
     accurate enough for quoting, and is speaker separation accurate enough
     for "who said what"?
   - Data: the two Probe C meetings (one clean, one noisy, Step 11), plus at
     least 2 AMI meetings in the distant-microphone condition; at least 60
     minutes in total, at least 30 minutes per condition (clean / noisy).
   - Metrics: WER (word error rate); DER (diarization error rate, with the
     standard 0.25 s forgiveness collar) and its parts (missed speech, false
     alarm, speaker confusion); "me vs others" accuracy using the voice
     enrolment; real-time factor (processing time ÷ audio length) on the
     laptop emulation profile.
   - **Usable (draft): WER at most 25 % on clean and at most 40 % on noisy;
     DER at most 30 % on clean; "me vs others" accuracy at least 90 %.
     Unusable: DER above 45 %, which makes named attribution misleading.**
5. **Decision table** (copied into the phase overview Gate 1): for each
   probe, an acceptable / unclear / unacceptable row with the scope change
   for Phases 4.1, 5.1 and 5.2.
6. **Stopping rules**: each probe runs once on the pre-registered data. A
   bug fix rerun is allowed and logged; changing data or thresholds after
   seeing results is allowed only as a separately labelled "exploratory"
   analysis, never replacing the pre-registered one.
7. **Sign-off**: the user approves the thresholds; if possible the
   supervisor sees them before the probes run (an email is enough). The
   date goes into the document.

## Open decisions

- **Probe A threshold values.** Options: (a) keep the drafts (10 % invention,
  40 % small-object miss); (b) stricter (5 % invention) — appropriate if the
  VLM is meant to be the only source for "where are my keys"; (c) a
  cost-based rule: unacceptable if, in the state-change scripts, VLM errors
  would make "where are my keys now" wrong more than 1 time in 5 — closer to
  what the user experiences, but needs Step 10 data to compute. The user
  chooses before Step 15.
- **Probe B fairness: what the VLM path is given.** Options: (a) VLM sees
  the same frames as the cheap path at a fixed rate (e.g. 1 fps) — equal
  input; (b) VLM sees only frames where the hand tracker fired — equal
  triggers, cheaper VLM; (c) both. (c) is fairest and costs only compute.
- **Probe C thresholds.** Options: (a) keep the drafts; (b) define
  usability by downstream effect (e.g. at most 1 in 5 `who_said` answers
  wrong because of speaker confusion), measured later in Phase 5.1;
  (c) both: drafts now, downstream check later.

## You test this

1. Read the pre-registration. For each probe, say out loud what you will
   do if the result is "unacceptable". If you cannot say it, the decision
   table is not concrete enough.
2. Choose the three threshold options above.
3. Send the document to your supervisor (I will draft a short cover note).

## How this number could be lying

This step creates no numbers; it protects the next ones. The risks:

- Thresholds set so loose that everything passes. Each threshold has a
  sentence saying why a worse result would hurt the user.
- Thresholds set by looking at published numbers from different datasets
  (not comparable). Thresholds are tied to user impact, not to papers.
- The document edited after results come in. Git history shows it; edits
  after the probe date are listed in a changelog section at the bottom.

## Verification

- [ ] `preregistration.md` covers Probes A, B, C with every field listed in
      "What".
- [ ] Wilson interval function implemented and checked against a known
      value (for example 10 out of 100 gives roughly 5.5 % to 17.4 %).
- [ ] Thresholds chosen by the user; supervisor informed (date recorded).
- [ ] Committed (or, if the repo is not yet a git repository, the file's
      hash and date recorded in `.memory/` and sent by email) before
      Steps 15, 19 and 21.

## Files changed

- [NEW] `docs/results/phase-3.1/preregistration.md`
- [NEW] `src/probes/__init__.py`, `src/probes/common.py` (Wilson interval,
  seeded sampling helper, results writer)
- [MODIFY] `README.md`

## Dependencies

- Step 01 (categories), Step 02 (slot fields used in metrics).
- Must be finished before Steps 15, 19, 21 run (it does not need any
  recordings).

## Common issues

- Overly detailed pre-registration becomes impossible to follow exactly.
  Keep it to what decides the outcome; everything else is "exploratory".
- Forgetting cost metrics: a probe that passes on accuracy but costs 10× more
  compute is not a pass for a phone. Every probe reports cost.
