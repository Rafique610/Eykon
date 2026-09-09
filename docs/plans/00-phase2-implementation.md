# Phase 2 Implementation Plan — Persistent Memory App (Android Port)

**Goal:** Port the validated Phase 1 architecture (capture → embed → store →
retrieve → generate) to a native, fully offline Android app, and add voice as a
second capture method.

**Success criteria:**
- App installs and runs on a real arm64 Android device
- User can add text memories and voice memories (Whisper transcribes on-device)
- User can ask a question and get a grounded answer generated on-device via
  Gemma 4 E2B / LiteRT-LM
- The 2.4GB model downloads on first launch with progress and a checksum check
- Runs fully offline once setup is complete

---

## Tech Stack

| Layer | Tool | Why |
|---|---|---|
| Language | Kotlin | Native Android target |
| Storage | Room (SQLite) | Direct port of the Phase 1 schema, including FTS5 for BM25 search |
| Speech-to-text | Whisper (on-device) | User's confirmed choice; produces a clean transcript that reuses the existing text pipeline |
| Embedding & Re-ranking | ONNX Runtime / LiteRT | Run `bge-small` and `ms-marco` cross-encoder entirely on-device |
| Retrieval | Hybrid Pipeline (Dense + Sparse + Re-rank) | Plain dense search fails on semantic queries (20% Hit@1). Phase 1.1 proved hybrid hits 93%. |
| Generation | Gemma 4 E2B (.litertlm) via LiteRT-LM Android (Kotlin) API | Same model/runtime already validated on the Phase 1 desktop prototype |
| Model delivery | WorkManager-driven download on first launch | 2.4GB model can't be bundled in the APK |

---

## Steps

| # | Step | Depends On |
|---|---|---|
| 01 | Android Project Setup + Room Storage | — |
| 02 | Text Capture (Ported Loop, No ML Yet) | 01 |
| 03 | LiteRT-LM Generation Integration | 01 |
| 04 | On-Device Embedding + Hybrid Retrieval | 01, 03 (shares the ML runtime setup) |
| 05 | Whisper Voice Capture | 02 |
| 06 | Full UI (Text + Voice + Retrieved Memories) | 02, 03, 04, 05 |
| 07 | Integration Test on Real Device + Polish | 01–06 |

---

## Dependency Graph

```
Step 01 (Setup + Storage)
  ├── Step 02 (Text Capture) ──────────────┐
  ├── Step 03 (LiteRT-LM Generation) ──┐    │
  │                                    ├──▶ Step 04 (Embedding + Retrieval)
  │                                    │        │
  └── Step 02 ──▶ Step 05 (Whisper) ───┘        │
                                                  ▼
                                    Step 06 (Full UI) ──▶ Step 07 (Integration Test)
```

Step 03 is deliberately isolated from retrieval at first — it proves LiteRT-LM
generation works on-device using hardcoded/canned context, before wiring it to
real retrieved memories. This separates "does the model run on this phone at
all" risk from "does retrieval feed it the right thing" risk.

---

## Why this order

Text capture (Step 02) comes before anything ML-related so the storage loop is
proven native on Android before any model risk is introduced — this mirrors how
Phase 1 started with capture and storage before embeddings.

LiteRT-LM generation (Step 03) comes next and deliberately skips retrieval at
first. The biggest unknown in Phase 2 is "does a 2.4GB model actually run
acceptably on the test device," and that question should be answered in
isolation, with a fixed canned prompt, before retrieval is layered on top of it.

Embedding + retrieval (Step 04) comes after generation because it depends on
the same on-device model runtime being set up and working. This step implements the full Phase 1.1 hybrid retrieval pipeline to guarantee 93%+ accuracy on mobile.

Whisper (Step 05) is deliberately late. It's the second capture method, not the
core loop, and any transcription quirks are easier to debug once the rest of the
pipeline (storage, retrieval, generation) is already known to work with typed
text.

Integration testing (Step 07) must happen on the real arm64 device used
throughout — not the emulator, which likely can't run the LiteRT-LM native path
at all.

---

## Working Cadence

Same as Phase 1: read the step doc, make the flagged decisions, implement,
verify on the real device, move on.
