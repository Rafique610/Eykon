# Mid report: answers to the open items (draft v2)

Written 15 October 2026 from the repository, the day logs (`.memory/`), the result files in
`docs/results/` and the Synverk board (project Eykon). Where the repository cannot know the answer,
the item says **TEAM TO FILL** and what is needed. Nothing here is guessed.

Repository state used: branch `feature/video-memory`, 54 commits, last pushed commit `a3bc0d5`; the
YOLOE-11L change to the app (15 Oct, 09:53) is built, installed on the Pixel and tested, not committed yet.

---

## A. Missing items

### 1. Cover page names (Dean, Director of the Campus, FYP Coordinator)
**TEAM TO FILL.** No names are in the repository. Use the names exactly as the department's FYP
template or notice gives them.

### 2. Meeting records (Appendix F)
**TEAM TO FILL**, from your own notes. What the repository does record, as a starting point:
- **First defense:** the panel did not accept it; a re-defense is required (`docs/domain/eykon/index.md`).
- **Latest panel feedback** (`docs/new/handoff-context-for-plan-writer.md`): the idea is good and well
  defended, but does it really need an LLM? Three possible complex-computing components: video keyframe
  extraction, memory hierarchy management, and performance and thermal management. The supervisor asked
  to explore the project without an LLM (embeddings, object detection).
- **Supervisor demo:** Thursday 15 October 2026, 3 PM (this meeting: add what was decided).

For each meeting: date, who attended, what was decided, next steps.

### 3. Android test results (Appendix C)
**Do not run `gradlew connectedAndroidTest` on the Pixel.** It uninstalls the app first, which deletes
the stored memories and the models on the phone (the 2.6 GB Gemma file among them). The project runs
phone tests with `adb install -r` and `adb shell am instrument` instead (rule in the team's notes).

Counts today:

| Kind | Tests | Last run | Result |
|---|---|---|---|
| JVM unit tests (`gradlew testDebugUnitTest`) | 102 (103 at the last commit; the YOLOE change replaced 3 OWLv2 / picking tests with 2 YOLOE tests) | 15 Oct, 09:40 | all pass |
| Instrumented tests (`app/src/androidTest`, `@Test` count) | 103 | 15 Oct, 09:40–10:00, by class with `am instrument` | DetectorGolden 2, OptionAPhone 3, VideoScene 8, VideoWorker 8, VideoFinish 7, VideoLink 7, VideoLatest 12, VideoEmbedTexts 9, VideoEmbedImages 8, VideoDedup 7, VideoSearch 6: all pass |
| Python tests (`task test`) | 14 | not re-run today | |

The benchmark-type instrumented classes (PerceptionBenchmark, KeyframeBenchmark, ObjectCropBenchmark,
Hybrid / Owl / YoloePhoneBenchmark, VectorStorageSpike) are measurements, not pass / fail tests, and
were run separately; their outputs are in `docs/results/`.

To attach, run and screenshot:
```
cd android
gradlew.bat testDebugUnitTest
adb -s <pixel> shell am instrument -w -e package com.eykon.memory.video com.eykon.memory.test/androidx.test.runner.AndroidJUnitRunner
```
(The package run also starts the benchmark classes; run the classes listed above one by one if you only
want pass / fail.)

### 4. Who did what
**TEAM TO FILL.** All 54 commits are under one account (Rafique610). From the day logs, the work
from 12 to 15 October was done in sessions run by Rafique with an AI coding assistant (Claude Code):
the phone pipeline (EYKO-9 to 16), the keyframe tests, the VLM benchmark, the detector comparison, the
D-FINE / OWLv2 / YOLOE phone runs and the app changes. Recording the own clips was done "with my mates"
(day log, 14 Oct): name who recorded and who appears in them. The repository does not show what Taha
and Zara built or measured; each member should add one or two lines (and links to forks, cards or
files if they have them).

### 5. AI tool disclosure (Chapter 8.5)
Known from the repository and logs:
- **Claude Code** (Anthropic; Claude Opus models), used for: writing and changing Python and Kotlin code,
  running laptop benchmarks and phone tests over adb, writing result documents, drawing the Synverk
  flows, and **making most evaluation labels** (marked `marked_by = ai` in the label files).
- **Synverk** (project board) through its MCP connector, used by the assistant to read cards and post results.

**TEAM TO FILL:** any other tools members used (for example ChatGPT, Copilot, Gemini) and for what,
including the source of the detector suggestion pasted in on 14 October, if it came from an AI tool.

### 6. Use Case Diagram (Section 4.2)
Recommendation: draw it from UC-01 to UC-10, with the user as the actor and the phone app as the system
boundary. I can draw it (as an image or a Synverk flow) once you confirm the ten use cases are final.

### 7. Appendix B (Detailed Requirements)
Recommendation: move the requirements traceability table and the extra use cases into Appendix B, and
leave a one-line pointer in Chapter 4. The appendix should not stay as template text.

### 8. Signatures and similarity
**TEAM TO FILL / check the department's rules.** Adding the submission date is usual. Whether a
Turnitin similarity percentage must be stated is a department rule; the repository has no record of it.

---

## B. Assumptions to confirm or correct

### Project and panel
**9. Which defense the comments came from.** The repository calls them "Panel feedback (latest)"
(`docs/new/handoff-context-for-plan-writer.md`) and separately says "panel rejected first defense; re-defense
required". It does not say which session the comments came from. **TEAM TO CONFIRM.**

**10. "Hybrid".** Not defined in the repository's current docs. The design notes say "nothing leaves the
device at runtime" and "zero network calls at runtime". If the report keeps an optional online mode,
**TEAM TO CONFIRM** it, because it contradicts those lines; otherwise describe the project as offline only.

**11. Supervisor and co-supervisor.** Not in the repository. **TEAM TO CONFIRM.**

**12. Start date.** Correct: first commit `51dc3a1` on **5 September 2026**.

### Targets and numbers
**13. Targets.** The measured baseline (`docs/plans/phase-3-vision/15-step15-honest-audit.md`, Infinix
Note 12): 11.1 s per query, 4.68 W average, 58.9 °C SoC. **Check the energy figure:** 11.1 s × 4.68 W is
about **52 J**, not 58.56 J (58.56 J would need about 12.5 s). Use the number from the measured log, or
recompute. Setting targets equal to the baseline means "no worse than today"; the team should decide
whether it wants an improvement target instead. Hit@5 ≥ 80 % is below the measured 93.3 % on the laptop
(499 memories, 30 questions). **TEAM TO CONFIRM** all five.

**14. Acceptance tests (Table 4.10).** Reasonable and measurable. "Zero network requests in airplane mode"
fits the offline design. **TEAM TO CONFIRM.**

**15. Risk ratings.** Your judgment; nothing in the repository contradicts it. Add two risks the work has
shown: AGPL models (YOLOE) need a licence decision before release, and MobileCLIP-S2 is under a
research-only licence (already in item 21).

### Phones
**16. Correct with one change.** Pixel 9 Pro XL is the capable phone (all video tests so far). The domain
doc says the **Samsung A32 is the modest phone, standing in for the Infinix Note 12** for video; the
Infinix was used for the earlier text-RAG measurements (4.68 W, 11.1 s). No video test has run on the A32
yet.

### Plan and owners
**17. Owners.** The repository does not record owners. Note that the detector comparison and the first
detection stage are already built (by the sessions in item 4), so Zara's Iteration 3 "detection" item
should become tuning and evaluation of detection (card EYKO-47), not building it. **TEAM TO CONFIRM.**

**18. FYP-II dates.** From your Gantt; nothing in the repository contradicts them. **TEAM TO CONFIRM.**

**19. Photo / OCR to Iteration 2.** Consistent with the repository: no photo or OCR code exists yet.

### Detection and video
**20. Yes, decided and done.** YOLOE-11L replaced OWLv2 in the app on 15 October (09:53): stage
`small_objects` runs YOLOE on every kept frame for keys and earbuds; D-FINE S (Objects365) and
YOLOX-Tiny stay in the scene step. Pixel figures: 55 of 87 own things found (OWLv2 version: 50), about 43 s
per 75 s clip (OWLv2 version: about 70 s). In the app after reprocessing: keys in 6 captions (all right),
earbuds in 4 (2 right, 2 false). Cut-off tuning parked as card **EYKO-47**. The change is tested but not
committed yet at the time of writing.

**21. Correct.** AGPL models are allowed while the project is academic (`docs/invariants/tooling.md`,
changed 14 Oct); a licence decision is needed before any release. MobileCLIP-S2 weights are under the
Apple ML Research Model License (research and academic use only, never shipped in the app package).

**22. Labels.** As far as the repository shows, **no**: the own-clip labels
(`docs/results/detectors/own-presence-2026-10-14.csv`, 50 frames) and the 44-frame presence labels
(`docs/results/perception/presence-2026-10-13.csv`) are all `marked_by = ai`, written before any model
ran. Contact sheets were checked by eye only to confirm the clips match their log. **TEAM TO FILL** if a
person has checked any since.

**23. Correct.** The phone uses float32 BLOB vector tables searched in memory (sqlite-vec was dropped,
EYKO-31), FTS4 for the caption keyword index (`video_texts_fts`), and the measured detectors (YOLOX-Tiny,
D-FINE S, YOLOE-11L), not YOLO11n. Say the diagrams show the planning design.

**24. Gantt.** Fine to leave as the original plan if the caption says so; add one line that detection is
now YOLOX-Tiny + D-FINE + YOLOE-11L.

### Stated as planned, not built
**25–27. Correct.** No Android Keystore code exists (NFR-13 not built). Temporal filter, question parser,
HyDE, CLAP sound vectors, faster-whisper on the phone, multi-list RRF on the phone, resource manager and
thermal switching are not built (cards EYKO-7, 8, 13, 17 to 24 are in the backlog). Smart glasses: not in
the repository.

---

## C. Honest gaps: two need updating

- **Phone search of typed memories by keyword only:** correct for typed memories. Note that video captions
  on the phone already have both a keyword index and bge-small text vectors (EYKO-12), and frames are
  searched by MobileCLIP vectors.
- **Voice / Whisper:** consistent with the repository (no phone Whisper engine yet; EYKO-8 in backlog).
- **Keyframes 31 vs 34 of 35:** correct, from `docs/results/2026-10-13-keyframes-slots-on-phone.md`
  (sharpest of each 3 s slot: 31; uniform: 34; same 44 frames). Add that the slot method cut phone
  processing from 137.5 to 32.6 s per minute of video, and that on EPIC-KITCHENS it found 151 of 158
  moments against 153 for uniform.
- **Small things: update.** Now **55 of 87** own things with the YOLOE version (Pixel scores), earbuds
  5 of 13; in the app's captions earbuds are 2 right and 2 false.

## D. Resolved conflicts: one row and the counts need updating

| Topic | Change |
|---|---|
| Detection | **YOLOX-Tiny + D-FINE S Objects365 in the scene step; YOLOE-11L on every kept frame for keys and earbuds** (OWLv2 on MobileCLIP-picked frames was used for half a day, 15 Oct, then replaced) |
| Counts | 220 tests = 14 Python + 103 JVM + 103 instrumented is right at the last commit; after the YOLOE change it is 14 + 102 + 103 = 219. 54 commits on `feature/video-memory`; one more when the YOLOE change is committed |

The other rows (Gemma 4 E2B on LiteRT-LM; Room + FTS4 with BLOB vectors; cheap filters, sharpest frame
per 3 s slot, dHash and MobileCLIP dedup; L0 to L3 experiment) agree with the repository.
