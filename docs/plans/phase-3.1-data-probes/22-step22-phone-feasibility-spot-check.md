# Phase 3.1 Step 22 — Phone Feasibility Spot Check for Shortlisted Models

## What

The phase's phone exam, sized for a probe phase (not a full parity gate):
run each shortlisted model **once, on a small fixed input, on both phones**,
and measure what it really costs there:

- Vision: the Step 17 hand model and image-text model on 30 probe frames;
  Gemma 4 E2B slot prompt on 10 probe frames (LiteRT-LM, already in the
  app).
- Speech: the Step 20 VAD, ASR sizes and speaker embedding model on a fixed
  5-minute meeting excerpt.
- Measured per model and phone: load time, latency per frame or real-time
  factor for audio (P50 and worst), peak memory of the app process, battery
  temperature before and after, thermal status changes, energy where the
  phone reports current (as in the existing Pixel / Infinix KPI scripts).
- **Output agreement**: for the same inputs, compare phone outputs with the
  laptop outputs from Steps 15, 18, 21 (same top-1 object for the image-text
  model, same hand count, transcript WER between laptop and phone runs).

Output: `docs/results/phase-3.1/phone-spot-check.md` and the measured
laptop-to-phone slowdown factor per model.

## Why

- Roadmap §4: "laptop is the lab, phone is the exam, every phase ends with an
  exam". For a probe phase, the exam question is simple: can the candidates
  that won on the laptop actually run on our phones, and at what cost?
- A probe winner that takes 3 seconds per frame on the Infinix changes the
  Gate 1 decision. Better to know now than in Phase 4.1's parity gate.
- The roadmap requires the slowdown factor to be **measured** per component,
  never assumed ("2–5×" was assumed in Phase 3).
- Known phone facts so far (from the handoff doc): Infinix averaged 4.68 W
  and 58.9 °C SoC in a query-only run; Pixel 4.7 s per query at 1.42 W. Those
  were LLM queries; nothing is known yet about the cheap models.

## How to implement

1. **A debug benchmark screen** in the app (next to the Step 06 capture
   screen): loads one model at a time, runs it on fixed inputs pushed by ADB
   (`/sdcard/Android/data/<package>/files/probe_inputs/`), writes a JSON
   result file. One model at a time keeps memory measurements clean.
2. **Runtimes**: MediaPipe Tasks for the hand model; LiteRT or ONNX Runtime
   Mobile for the image-text model (whichever Step 17 verified); LiteRT-LM
   for Gemma (existing `LiteRTGenerator.kt` code path); whisper.cpp or
   sherpa-onnx for speech (Step 20). New Android dependencies are listed and
   approved by the user before adding them to Gradle.
3. **Protocol**: phone at room temperature (battery temperature recorded),
   screen on, airplane mode, release build if possible (debug noted
   otherwise), 3 warm-up runs then measured runs, both phones the same day.
4. **Laptop comparison**: the same inputs and the same model files on the
   laptop under the emulation profile; slowdown factor = phone latency ÷
   laptop latency, per model and phone.
5. **Agreement**: phone vs laptop outputs compared; any difference larger
   than the tolerance (to be set: e.g. same top-1 object on at least 90 % of
   frames) is investigated (colour format, resize, normalisation are the
   usual causes) and documented.
6. **Pull and report**: `task pull-probe-results`, then
   `src/probes/phone_report.py` builds the tables.

## Open decisions

- **How far to go when a runtime is missing.** Options: (a) if a model has
  no working Android runtime within a day of effort, record "not run on
  phone" and its reason — honest, keeps the phase short; (b) push through
  with a conversion (e.g. to ONNX or LiteRT) — more complete, may take days;
  (c) replace it with the next shortlisted model that does run. The draft
  prefers (a) then (c).
- **Release vs debug build.** Options: (a) release build — real numbers,
  needs signing setup; (b) debug build — fast, slower numbers; (c) debug now,
  release in the Phase 4 parity gate. Must be stated in the report either
  way.

## You test this

1. Run the benchmark screen on the Pixel, then the Infinix, same day. Watch
   the screen while it runs; note if the phone becomes noticeably warm or
   the UI freezes.
2. Check the agreement table: do the phones "see" the same objects in the
   30 frames as the laptop did?
3. Read the slowdown factors. Which model would you not want running all
   day on the Infinix?

## How this number could be lying

- A few minutes of running says nothing about sustained thermal throttling
  over 30 minutes or a day (Phase 6 does that). Results are labelled
  "short run".
- One model at a time hides contention: in the product, several models
  share CPU and memory. Noted as a limitation; Phase 4 and 6 measure
  combinations.
- Battery-current readings on some phones are coarse or averaged; energy
  numbers are reported with the reading method.

## Verification

- [ ] Every shortlisted model run on both phones, or a written reason why
      not.
- [ ] Latency P50 and worst, peak memory, temperature change and thermal
      status per model and phone.
- [ ] Measured slowdown factor per model and phone.
- [ ] Phone–laptop output agreement table with explanations for
      differences.
- [ ] Build type and protocol recorded.

## Files changed

- [NEW] `android/.../probes/ProbeBenchmarkScreen.kt`,
  `ProbeBenchmarkRunner.kt` (debug only)
- [MODIFY] `android/app/build.gradle.kts` — only approved runtime
  dependencies
- [NEW] `src/probes/phone_report.py`
- [NEW] `docs/results/phase-3.1/phone-spot-check.md`
- [MODIFY] `Taskfile.yml` — `push-probe-inputs`, `pull-probe-results`
- [MODIFY] `README.md`

## Dependencies

- Step 06 (debug screen pattern, Android data layer present), Steps 16, 19,
  21 (laptop results and chosen models).

## Common issues

- Image-text models need exact preprocessing (resize, crop, normalisation
  constants); a mismatch gives plausible but different results. Golden input
  tensors from the laptop help.
- The Infinix may lack an NNAPI / GPU path for some models; measure CPU and
  note it.
- Large model files on the phone: push once with ADB, never bundle in the
  APK for a spike.
