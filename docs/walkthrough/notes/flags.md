# Running list of flags

Things noticed along the way: doc-vs-code mismatches, dead code, stubs,
suspected bugs, risks. Phase 1 confirms or clears each one; Phase 2 moves
them into `06-open-questions.md`. "Confirmed" means the code was read and
the citation checked. "To check" means it still needs the stage deep dive.

| # | Kind | What | Evidence | Status | Stage |
|---|---|---|---|---|---|
| F1 | doc-mismatch | README lists 9 pipeline stages; the code has 10 (`small_objects` is missing from the README) | `README.md:63` vs `android/app/src/main/java/com/eykon/memory/video/VideoPipeline.kt:16-27` | confirmed | s01 |
| F2 | doc-mismatch | README describes `components/MemoryHeaderBar.kt`; no such file exists (`MemoryCountBadge.kt` does) | `README.md:36`; `git ls-files` | confirmed | s09 |
| F3 | stale doc | `docs/additional/architecture-overview.md` describes folders that do not exist (`capture/text.py`, `retrieval/embedder.py`, `storage/repository.py`, `generation/llm.py`) and Ollama generation | `docs/additional/architecture-overview.md:21-34`, `:8` | confirmed | s10 |
| F4 | stub | `WhisperTranscriber.transcribe` never runs a model: it returns the text "Voice memo (N s recorded)"; the README says it transcribes | `android/app/src/main/java/com/eykon/memory/capture/WhisperTranscriber.kt` (`transcribe`, the "inference placeholder" comment); `README.md:25` | confirmed | s09 |
| F5 | parity gap | The phone's text `SearchService` is built without an embedder or re-ranker, so only keyword search runs; `core.md` "Phase Parity" requires the laptop's retrieval on the phone. The domain doc admits it | `android/app/src/main/java/com/eykon/memory/MainActivity.kt` (`SearchService(dao)`); `docs/invariants/core.md:61`; `docs/domain/eykon/index.md:92` | confirmed | s09 |
| F6 | dead code | `LocalEmbedder`, `TokenizerHelper`, `LocalCrossEncoder` are never constructed by app code | `README.md:60` ("never switched on"); to check with a usage search | to check | s09 |
| F7 | dead config | `ollama` dependency and `OLLAMA_*` settings are unused by any code | `pyproject.toml`; `src/config.py:19-20`; no other `ollama` match in `src/` | confirmed | s10 |
| F8 | stale doc | Step 06 plan is titled LiteRT-LM but still contains the Ollama code and error table | `docs/plans/done/✅ 06-step06-generation-llm.md:15` vs `:72-157` | confirmed | s10 |
| F9 | doc-mismatch | Python version: `.python-version` is 3.10 and `requires-python = ">=3.10"`, the domain doc says 3.11+ | `.python-version`; `pyproject.toml:6`; `docs/domain/eykon/index.md:90` | confirmed | cross-cutting |
| F10 | portability | Android tasks call `cmd.exe /c gradlew.bat` with a hard-coded Windows `JAVA_HOME`; many benchmark scripts hard-code `D:/eykon-cache` | `Taskfile.yml:75-87`, `:197-205`; `grep -l "D:/eykon-cache" src/benchmarks` (10 files) | confirmed | s12–s14 |
| F11 | reproducibility | Lab extras are fetched unpinned with `uv run --with` (onnxruntime, open_clip_torch, ultralytics, transformers, rfdetr, mediapipe, scenedetect, onnx, onnxscript, onnxslim, tokenizers, sqlite-vec), so a re-run may get different versions than the measured one | `Taskfile.yml` (`--with` arguments); none of them are in `uv.lock` | confirmed | s12–s14 |
| F12 | broken task | `test-vision-integration` and `benchmark-vision` use `test_video.mp4`, deleted in commit `23147b0` | `Taskfile.yml:216`, `:229`; `git show --stat 23147b0` | confirmed | s11, s15 |
| F13 | dead files | `scratch/litertlm/` and `scratch/litertlm.zip` (about 67 MB of committed binaries); Gradle takes LiteRT-LM from Maven (`litertlm-android:0.16.1`) | `android/app/build.gradle.kts`; `du` of tracked files | to check | s09 |
| F14 | data in git | `scratch/memories.db`, `-wal`, `-shm` are committed database files | `git ls-files scratch` | confirmed | s15 |
| F15 | portability | `scratch/*.py` hard-code a Windows adb path, a LAN IP and adb serials | `scratch/endurance_stress_test.py`, `scratch/profile_device_kpis.py`, `scratch/sync_db_infinix.py` (top constants) | confirmed | s15 |
| F16 | unused output | `audio16k.wav` is written but nothing reads it. `audio_segments`, `transcript_chunks`, `audio_windows` and `audio_vec` are read (counts in `VideoRepository.kt:59-60`, checks in `VideoLink.kt:29-37`, the union in `VideoEmbedTexts.kt:27`) but no code writes them (speech is card EYKO-8, sounds EYKO-13) | `android/app/src/main/java/com/eykon/memory/video/VideoSplit.kt:52`; grep for `INSERT INTO audio_*` / `transcript_chunks` finds none; `docs/domain/eykon/index.md:96-97` | confirmed | s02, s06 |
| F17 | built but unused | Captions get an fts4 keyword row and a bge vector, but the moment search uses only frame vectors (the Ego4D hybrid test was worse: "Drop for now") | `VideoSearch.kt:24-34`; `docs/results/2026-10-21-ego4d-improvements.md` row 3 | to check | s06, s08 |
| F18 | doc-vs-code gap | Ego4D change 4 ("last seen" with crops of any object) is marked **Keep** but does not appear to be built into the app | `docs/results/2026-10-21-ego4d-improvements.md` row 4; `VideoLatest.kt` | to check | s07 |
| F19 | privacy risk | `android:allowBackup="true"` in an app that keeps a private memory database; the backup rules files need reading | `android/app/src/main/AndroidManifest.xml:17` | to check | s09 |
| F20 | oddity | `src/benchmarks/experiment_a1.py` starts with a UTF-8 BOM (Python runs it, but tools that parse decoded text fail) | `ast.parse` error at line 1 | confirmed | s15 |
| F21 | misleading name | `test_litert_vision.py` at the repo root is not a pytest test (`testpaths = ["tests"]`) and writes `data/dummy_test_image.jpg` | `pyproject.toml:29-30`; the file | confirmed | s11 |
| F22 | rule breach | Files over the ~300-line limit in `core.md`: `src/benchmarks/data.py` (1842, mostly data), `src/ui/app.py` (466), `src/benchmarks/run.py` (328), `detector_bench.py` (306), `cross_pipeline.py` (302) | `wc -l`; `docs/invariants/core.md:13` | confirmed | s10, s13, s15 |
| F23 | broken links | `docs/docs/index.md` links point at `file:///c:/Users/rafique_/Desktop/New%20folder/FYP_Demo/...` | `docs/docs/index.md:15-32` | confirmed | cross-cutting |
| F24 | dev hack | `src/ui/app.py` reloads its own imports with `importlib.reload` at start-up | `src/ui/app.py:30-59` | confirmed | s10 |
| F25 | incomplete example | `.env.example` lists only the Phase 1 settings; none of the `VLM_*`, `video_*`, `detector_*` or `scene_*` settings | `.env.example` vs `src/config.py:32-88` | confirmed | cross-cutting |
| F26 | guard by comment | `REDO_AFTER` must never name `split` or `filter` (dropped frame files are deleted in `finish`); only a comment enforces it | `VideoPipeline.kt:47-53` | confirmed | s01, s07 |
| F27 | environment | `data/` and `models/` do not exist on this machine; datasets live in `D:/eykon-cache` on the author's PC, so no benchmark can be re-run here | `ls`; F10 | confirmed | s12–s15 |
| F28 | process | `AGENTS.md` ties each step to a Synverk card; the `synverk` MCP server needs authentication in this session, so no card was read or moved | `.mcp.json`; `AGENTS.md` "Working one step at a time" | confirmed | process |
| F29 | dead code | `GenerationTestScreen` and `GenerationTestViewModel` are referenced by no other file; the navigation has only Capture, Ask and Video | `android/app/src/main/java/com/eykon/memory/ui/navigation/AppNavigation.kt:23-27`; grep | confirmed | s09 |
