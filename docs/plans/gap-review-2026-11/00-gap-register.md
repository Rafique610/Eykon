# Gap review — November 2026

Started 2 November 2026. A time-boxed audit of the video pipeline as built, before new features.
Not a restart: every finding becomes one card, fixed in the order at the end.

**Read from:** the phone code (`android/app/src/main/java/com/eykon/memory/`), its tests
(109 JVM, 104 on-device), `docs/results/`, `docs/domain/eykon/index.md`, `README.md`,
`docs/invariants/`, and the day logs up to 1 November. **Not read:** the Synverk board (sign-in
needed), so card states changed there after 22 October are not reflected.

## The questions asked of every stage

1. **Source:** where does each constant come from: tuned on data, a model's documented default,
   or a card's starting value?
2. **Labels:** were the labels behind its result checked by a person?
3. **Parity:** do the phone and the laptop agree, and does a test prove it?
4. **Docs:** do the README and the domain index say what the code does today?

Severity: **High** = would be attacked at the viva or hurts real use. **Medium** = weakens a claim or
costs time. **Low** = note it, fix when nearby.

## Register

### Thresholds

| # | Gap | Evidence | Sev. | Owner |
|---|---|---|---|---|
| G1 | Frame filter cut-offs were never tuned: dark 25, bright 235, blurry 60, still 6 / 0.10 | `video/FrameFilters.kt:26-32` ("not yet tuned"). On our 951 frames, sharpness averages per video run from 143 to 2,605 and only 6 frames fall under 60 (re-decode on the laptop, 22 Oct log). One fixed number cannot fit every scene. | High | Research |
| G2 | Detector and prompt cut-offs are untuned on our clips: YOLOX 0.35, D-FINE 0.5, YOLOE 0.25, place/action share 0.30 | `OptionA.kt:41-42`, `DfineDetector.kt:26`, `YoloeDetector.kt:28`: card start values or the models' documented defaults. Phone and laptop captions differ by a word in half the frames because objects sit near these cut-offs (`2026-10-20-ego4d-baseline.md`, phone section). | High | Research |
| G3 | Dedup cut-offs untuned: dHash ≤ 6 bits, MobileCLIP cosine ≥ 0.95 | `VideoDedup.kt:23-24`; the first keyframe run notes the 0.95 bar "lets most hand-held frames through" (`2026-10-12-keyframes-first-run.md:89`). | Medium | Research |
| G4 | Action smoothing (±6 s) may be fitted to set A | `OptionA.kt:75`; set B ranks the unsmoothed version higher (F1 18.2 vs 16.7, `2026-10-21-ego4d-improvements.md`). | Medium | Research |

Tuned on data and fine as they are: 3 s slots (EPIC-KITCHENS), crop match 0.87 (but see G5),
search windows 0.85 / 10 s (held-out set B), YOLOE gate 0.15 (held-out set B).

### Labels and evidence

| # | Gap | Evidence | Sev. | Owner |
|---|---|---|---|---|
| G5 | Four results rest on labels the AI assistant wrote, never checked by a person | `2026-10-13-eyko-9-perception-option-a.md:18` (YOLOX-Tiny choice), `2026-10-13-frame-search-probe.md:17` (search probe), `2026-10-13-eyko-15-crop-threshold.md:15` (the 0.87 cut-off), `2026-10-14-detectors-open-vocabulary.md:32` (own50, which picked YOLOE). Only the keyframe moments were reviewed (`keyframes/moments-2026-10-12-reviewed.csv`). | High | Evaluation |
| G6 | Too little of our own footage | Only S1-01 and S1-02 of the recording plan exist; sets 8 and 9 (EYKO-50) are not recorded. Ego4D gives 78 + 12 NLQ questions on set A, fewer on B: a direction, not a final score. | High | Evaluation |
| G7 | Filter decisions cannot be checked afterwards | The sharpness value is not stored, and dropped frames' pictures are deleted (EYKO-59). Re-decoding was the only way to measure G1. | Medium | Lead |

### Code

| # | Gap | Evidence | Sev. | Owner |
|---|---|---|---|---|
| G8 | Deleting or editing a text memory likely fails on the phone | `data/MemoryDatabase.kt:58,64` use FTS5's `('delete', …)` insert on an fts4 table: the same bug fixed for video texts on 12 Oct, flagged then for memories and still there. Not re-tested. | High | Lead |
| G9 | The retrieval rule and the video search disagree | `docs/invariants/core.md` (Phase Parity): phone retrieval = BM25 + dense + RRF. Video search is dense only, because hybrid made Ego4D results worse (EYKO-61). The decision is in a result file, not in the rule. | Medium | Lead (decide) |
| G10 | Videos only process while the app is in front | EYKO-44; an 8-minute clip stalled when another app was opened (`2026-10-20-ego4d-baseline.md`). | Medium | Lead |
| G11 | The same file can be added twice | Videos `142de7f3` and `b2ea85c0` on the Pixel are one file stored twice. | Low | Lead |
| G12 | Speech tables exist, nothing fills them | `transcript_chunks`, `audio_windows`, `audio_vec`: no writer until EYKO-8. The WAV is made and unused. | Low | — (roadmap) |

### Parity and devices

| # | Gap | Evidence | Sev. | Owner |
|---|---|---|---|---|
| G13 | The low-end phone never ran the video pipeline | The A32 only ran the vector spike (EYKO-31). The domain index promises results on both phones. | Medium | Evaluation |
| G14 | App-to-laptop parity checked on 4 clips, one phone | `2026-10-20-ego4d-baseline.md` phone section; golden tests cover filters, hash, detectors and perception. Enough for now; repeat after G1–G3 change the stages. | Low | Evaluation |

### Docs and tooling

| # | Gap | Evidence | Sev. | Owner |
|---|---|---|---|---|
| G15 | README is three weeks behind | Last changed in `99faff5` (EYKO-16, 16 Oct): no D-FINE, YOLOE, small_objects, search windows, action smoothing or YOLOE gate; the status lines still describe Phase 2 / 3 steps. `processes.md` asks for it on every step. | High | Lead |
| G16 | Domain index is stale | `docs/domain/eykon/index.md`: "Next milestone: 15 October", "EYKO-1 and EYKO-2 … awaiting a phone test", EYKO-3 "next". | Medium | Lead |
| G17 | Two broken tools | `src/benchmarks/frame_report.py` pull needs Python 3.12 (`extractall(filter=)`), the laptop has 3.10.6; `task test-android` / `build-android` call bare `gradlew.bat`, which fails in the agent's shell. | Low | Lead |
| G18 | Phone storage | 620 MB free of 109 GB on 22 Oct: the app could not be reinstalled. | Medium | Evaluation |
| G19 | Licences to re-decide before any release | MobileCLIP (Apple research licence), YOLOE (AGPL): allowed while academic (`docs/invariants/tooling.md`). | Low | — |

## Cards (Synverk, created 2 November 2026)

Every card is labelled `gap-review` plus its owner (`lead`, `research`, `evaluation`) or `decision`.

| Gap | Card | Waits for | Related older card |
|---|---|---|---|
| G1 filter cut-offs | EYKO-77 | EYKO-74, EYKO-73 | EYKO-48 (run together) |
| G2 detector / prompt cut-offs | EYKO-78 | EYKO-72 | EYKO-47 (absorbed) |
| G3 dedup cut-offs | EYKO-79 | EYKO-77 | EYKO-46 (dedup part) |
| G4 action smoothing | EYKO-80 | — | EYKO-60 |
| G5 human label check | EYKO-72 | — | |
| G6 own footage | EYKO-82 | EYKO-76 | EYKO-50 (the recording) |
| G7 store sharpness | EYKO-73 | — | EYKO-49 (shows it) |
| G8 memories trigger bug | EYKO-67 | — | |
| G9 retrieval ADR | EYKO-81 | EYKO-75 | EYKO-61 |
| G10 background check | EYKO-85 | EYKO-44 | EYKO-44 (the build) |
| G11 duplicate upload | EYKO-71 | — | EYKO-66 |
| G12 speech half-built | EYKO-86 | — | EYKO-7, EYKO-8 |
| G13 A32 first run | EYKO-84 | — | EYKO-34 (the gate) |
| G14 parity re-check | EYKO-87 | EYKO-77, 78, 79 | EYKO-34 |
| G15 README | EYKO-68 | — | |
| G16 domain index | EYKO-69 | — | |
| G17 tools | EYKO-70 | — | |
| G18 phone storage | EYKO-83 | — | |
| G19 licences | EYKO-88 | — | |
| Decision 1: "dynamic blur" | EYKO-74 | — | |
| Decision 2: retrieval rule | EYKO-75 | — | |
| Decision 3: recording scope | EYKO-76 | — | |

## Fix order

Each step is one card. The owner column above says who does it; steps with different owners run at the same time.

1. **Quick fixes (lead, about a day):** G8 trigger fix with a phone test; G15 README; G16 domain index; G17 tools; G11 if it stays one check.
2. **Human label check (evaluation):** G5. Check and correct the four label files; re-score the four results; note any change in each result file. Do this before tuning, because tuning on wrong labels tunes to the mistakes.
3. **Store what the filter measured (lead):** G7. One `sharpness` column (and brightness) per frame, written by `filter`. Cheap, and it makes G1 measurable on every future video.
4. **Adaptive filter cut-offs (research), with EYKO-48:** G1. Laptop benchmark of a cut-off relative to the median sharpness of nearby frames, against human-marked blurry and sharp frames. Port only if it wins.
5. **Detector, prompt and dedup cut-offs (research):** G2, G3, G4, on the checked labels from step 2 and held-out set B.
6. **Write the retrieval decision down (lead, with you):** G9, as an ADR: either the parity rule gets a video exception backed by EYKO-61, or hybrid comes back with better captions (Option C).
7. **Own footage and the second phone (evaluation):** G6 sets 8 and 9; G13 the pipeline on the A32; G18 phone storage first.
8. Then back to the roadmap: EYKO-44 (G10), EYKO-49, EYKO-62 on the phone, speech (G12).

## Open decisions

- **What "dynamic blur" means for the supervisor.** (a) A cut-off relative to the video: fits the
  measured spread (143–2,605), needs human-marked frames to tune. (b) Gaussian smoothing before the
  Laplacian (Laplacian of Gaussian): makes the measure less noisy, but a fixed cut-off still fails
  across scenes. (c) Both. Confirm with the supervisor before step 4.
- **G9:** amend the invariant for video (keeps today's measured best) or rebuild hybrid later
  (keeps the rule, needs better captions first).
- **G6 scope:** record all of sets 8 and 9, or only the actions EYKO-52 cannot get from public data.
