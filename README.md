# Persistent Memory App

A local-first personal memory app. Store details about your life (notes, facts, events, preferences), and query them using natural-language questions with locally-grounded retrieval-augmented generation (RAG).

> ✅ **Status:** Phase 1 Complete (End-to-End Pipeline) + Phase 1.1 Complete (Retrieval Quality Improvements).  
> 🔄 **Phase 2 In Progress:** Step 01, Step 02, Step 03, Step 04, Step 05 & Step 06 Complete (Android Setup + Room SQLite + Text Capture + LiteRT-LM + FTS & Hybrid Search + Voice Memo Capture + Full End-to-End RAG UI).
> 🔄 **Phase 3 In Progress:** Step 01, Step 02, Step 03, & Step 04 Complete (Literature Review, Env Setup, Extractor, & VLM Captioner).
> - Hybrid search Hit@5: **93.3%**
> - Exact factual questions Hit@1: **100%**
> - Android Target: **API 31 (Android 12)+** for Gemma 4 / LiteRT-LM

## Architecture

Built using a **feature-based file structure**:

### Android Core & Assistant (`android/`)
- `android/app/src/main/java/com/eykon/memory/data/`:
  - `MemoryRecord.kt`: Room SQLite entity mirroring the Phase 1 schema (`id`, `text`, `embedding`, `timestamp`, `source_type`, `metadata`).
  - `Converters.kt`: Room TypeConverter serializing `List<Float>` ↔ SQLite TEXT (JSON string) for the 384-dim vector.
  - `MemoryDao.kt`: Suspend CRUD methods (`insert`, `insertAll`, `getAll`, `getById`, `deleteById`, `count`, `deleteAll`, `searchFts`) + `getAllAsFlow()`.
  - `MemoryDatabase.kt`: Room SQLite database singleton (`memories.db`) with `fts4` virtual table synchronization and triggers.
- `android/app/src/main/java/com/eykon/memory/capture/`:
  - `TextCaptureService.kt`: Input validation, token-bounded chunking, and `MemoryRecord` assembly (supports `sourceType = "text"` and `"audio"`).
  - `AudioCaptureService.kt`: Low-level 16kHz 16-bit Mono PCM audio capture using Android `AudioRecord` with RIFF/WAVE header assembly.
  - `WhisperTranscriber.kt`: Resolves local Whisper model weights and transcribes recorded audio on background coroutines.
- `android/app/src/main/java/com/eykon/memory/retrieval/`:
  - `QueryExpander.kt`: Zero-latency concept expansion dictionary for abstract queries.
  - `SearchService.kt`: Hybrid retrieval combining FTS SQLite search, vector similarity, RRF fusion, and score attribution.
- `android/app/src/main/java/com/eykon/memory/assistant/`:
  - `PromptBuilder.kt`: Formats grounded RAG prompt with Phase 1 parity (7 strict guidelines + 5 few-shot examples).
  - `GenerationParams.kt`: Generation hyperparameters (`temperature: 0.3f`, `maxOutputTokens: 256`, `topK: 40`, `topP: 0.95`).
  - `ModelManager.kt`: Resolves path to `gemma-4-E2B-it.litertlm` and provides target ADB sideload instructions.
  - `LiteRTGenerator.kt`: On-device inference runner with background dispatch (`Dispatchers.Default`) and answer prefix cleaner.
- `android/app/src/main/java/com/eykon/memory/ui/`:
  - `navigation/AppNavigation.kt`: Material 3 Bottom Navigation switching between `Capture` (📝) and `Ask` (💬).
  - `components/MemoryHeaderBar.kt`: Top banner bar displaying app title, model status (`🟢 Ready` / `⚠️ Pending`), and reactive memory count badge (`📊 X`).
  - `components/RetrievedMemoryCard.kt`: Grounding transparency card displaying retrieved record text, similarity score, rank, and source badge.
  - `components/VoiceRecordButton.kt`: Compose button with runtime audio permission launcher and speech-to-text integration.
  - `screens/AddMemoryScreen.kt`: Jetpack Compose screen for text & voice capture with live recent memories list and memory header.
  - `screens/AskQuestionScreen.kt`: End-to-end question answering interface with typed/voice queries, staged loading indicators, synthesized Gemma 4 answer card with latency metrics, and retrieved memories attribution.
  - `viewmodels/AddMemoryViewModel.kt`: Compose ViewModel managing text/voice memory capture and Room StateFlow.
  - `viewmodels/AskQuestionViewModel.kt`: Compose ViewModel orchestrating Room SQLite, SearchService, and LiteRTGenerator with test dispatcher injection.
  - `theme/`: Material 3 theme (Color, Typography, Theme).
- `android/app/src/main/java/com/eykon/memory/`:
  - `MemoryApp.kt`: Application class managing lazy database singleton.
  - `MainActivity.kt`: Entry activity hosting bottom navigation between Capture and Ask tabs.
- `android/app/src/main/java/com/eykon/memory/video/` (video memory on the phone, cards EYKO-1 and EYKO-2):
  - `VideoSchema.kt`: The same video tables as the laptop's `src/video_memory/schema.py` (same names and columns), created on every open; the keyword index is fts4 because the phone's SQLite has no FTS5.
  - `VideoRepository.kt`: `insert`, `get`, `list` for the `videos` table, plain SQL with `?` parameters.
  - `VideoMetadata.kt`: Parsers for recording time and GPS, the 500 MB limit and the accepted types.
  - `VideoCapture.kt`: Copies a picked clip into `files/videos/<video_id>/`, reads recording time, length and GPS, refuses files with no video, adds the `videos` row.
  - `VideoJobs.kt`, `VideoPipeline.kt`, `VideoWorker.kt` (card EYKO-3): every saved video gets a job in the `jobs` table; one background worker runs the job's stages in order, saves the stage reached, retries a failing stage up to 3 times, and resumes interrupted jobs when the app next starts. `VideoPipeline.STAGES` is the list later cards add their stage to (empty for now). The worker only runs while there are jobs; it does not poll.
  - `VideoSplit.kt`, `FrameExtractor.kt`, `AudioExtractor.kt`, `MonoResampler.kt` (card EYKO-4, stage `split`): frames at 3 per second saved as JPEGs in `files/videos/<video_id>/frames/` (longer side at most 640 px, turned upright), one `frames` row each, and the sound as `audio16k.wav` (16 kHz, mono, 16-bit; silence if the video has no sound). Frames are read in one pass with the phone's video decoder; if that fails the stage falls back to reading frame by frame. Timings go to logcat under the tag `EykonVideo`.
  - `FrameFilters.kt`, `VideoFilter.kt` (card EYKO-5, stage `filter`): drops useless frames with plain maths, cheapest check first, stopping at the first check a frame fails: too dark, too bright, blurry (variance of the Laplacian), or unchanged since the last kept frame (pixel difference and histogram change). A dropped frame keeps its row and file with `kept = 0` and a `drop_reason`. The measures give the same numbers as OpenCV: `task golden-filters` (`src/benchmarks/filters_golden.py`) writes test pictures and OpenCV's values to `android/app/src/test/resources/filters/`, and `FrameFiltersTest` checks the Kotlin code against them. Thresholds are the card's starting values, not yet tuned.
  - `FrameHash.kt`, `VideoDedup.kt`, `ml/vision/ImageEmbedder.kt` (card EYKO-6, stage `dedup`): drops near-duplicates among the kept frames in two layers. (1) A 64-bit difference hash of each frame is stored in `frames.phash`; a frame within 6 bits of an earlier unique frame is a duplicate. (2) Frames that pass are embedded with MobileCLIP-S2 (ONNX Runtime, CPU); cosine 0.95 or more with an earlier unique frame is a duplicate. Duplicates get `drop_reason = duplicate of frame N`. Unlike the "unchanged" check, both layers compare with every unique frame so far, so a scene the camera returns to is stored once. Unique frames' vectors are saved in `clip_vectors.bin`. The model file is made with `task export-clip` and pushed to the phone (`adb push models/mobileclip_s2_image.onnx /sdcard/Android/data/com.eykon.memory/files/models/`); it is not in git or the app package. Its weights are under the Apple ML Research Model License (research and academic use only).
  - `ml/vision/ObjectDetector.kt`, `OptionA.kt` (card EYKO-9, perception Option A; not yet a pipeline stage and nothing is written to the database): `OptionA.describe(context, frameFile)` returns a `Perception` (objects with confidence and box, number of people, place, action; `caption` stays empty until Option C). Objects come from YOLOX-Tiny (Apache-2.0, official ONNX file, 20 MB, ONNX Runtime on the CPU, 80 everyday classes; keys and other small personal things are card EYKO-32). Tiny replaced Nano on 13 October 2026 after Nano found 4 of 32 everyday things in our frames and Tiny 18; `PerceptionBenchmarkTest -e detector yolox_nano.onnx` still measures the other file. Place and action are the best-fitting phrase from two fixed lists, scored with the frame's MobileCLIP vector, or nothing when the best share is under 0.30. The phrases' vectors are in `android/app/src/main/assets/scene_prompts.json`; the lists live in `src/config.py` (`MEMORY_SCENE_PLACES`, `MEMORY_SCENE_ACTIONS`) and `task golden-perception` (`src/benchmarks/perception_golden.py`) rewrites the file and the laptop's reference answer the phone test is checked against. Get the detector with `task pull-detector` and push it: `adb push models/yolox_tiny.onnx /sdcard/Android/data/com.eykon.memory/files/models/`. Measured results: `docs/results/2026-10-13-eyko-9-perception-option-a.md` (`PerceptionBenchmarkTest` on the phone, then `task eval-perception -- <json> <labels csv>`). `task probe-frame-search` (`src/benchmarks/frame_search_probe.py`) is a laptop check of typed-phrase search over frame vectors, results in `docs/results/2026-10-13-frame-search-probe.md`.
  - `VideoScene.kt` (card EYKO-10, stage `scene`): after `dedup`, writes one `scene_records` row for every frame still kept: the objects as JSON (`label`, `conf`, `box`), `action`, `place`, `people`, a one-line `caption` and `source` (`A`). The caption is plain words built from the fields by `buildCaption` (up to three different things surest first, then people, place, action; "nothing recognised" when all are empty), no model; an option that brings its own caption (Option C later) keeps it. `VideoScene.OPTIONS` maps an option letter to its describe function and `SCENE_OPTION` picks one. The stage reuses the image vectors `dedup` saved, deletes the video's earlier records first, and logs its time under `EykonVideo`. The Video tab's "stage n of 4" follows automatically. `VideoSceneTest -e clip clip1.mp4` prints a real clip's captions to logcat.
  - `VideoVectors.kt`, `VideoEmbedImages.kt` (card EYKO-11, stage `embed_images`): `VideoVectors` is the phone's copy of the laptop's `src/video_memory/db.py`: `put` stores a vector as a float32 little-endian BLOB (size-checked: 512 for `image_vec` and `audio_vec`, 384 for `text_vec`), `knn` reads a vector table into memory once and returns the nearest rows by dot product, `clearCache` drops the loaded copy; no SQLite extension. The stage writes one MobileCLIP vector into `image_vec` for every frame still kept, reusing the vectors `dedup` saved in `clip_vectors.bin` and running the model only for a frame that has none; it deletes the video's earlier vectors first. `VideoPipeline.STAGES` is now split, filter, dedup, scene, embed_images.
  - `ml/vision/ClipTokenizer.kt`, `ml/vision/TextEmbedder.kt`, `VideoSearch.kt` (core of card EYKO-19, search by typed phrase): `TextEmbedder.embed(context, phrase)` gives the phrase's 512-number MobileCLIP vector, in the same space as the frame vectors; `ClipTokenizer` is CLIP's tokenizer in plain Kotlin, reading its merge rules from `assets/clip_bpe_merges.txt`. `VideoSearch.frames(db, phrase)` returns the 20 stored frames closest to the phrase, best first, each with its video, time, picture file, likeness (cosine) and stored caption. It does not use the captions, so it finds things the detector has no name for. Not in it yet: date ranges and rewording (EYKO-18), latest sighting only (EYKO-15), ready-only videos (EYKO-16), a lowest likeness worth showing. The text model is made with `task export-clip-text` (`src/benchmarks/export_clip_text.py`, 254 MB, same research-only licence as the image model) and pushed: `adb push <file> /sdcard/Android/data/com.eykon.memory/files/models/mobileclip_s2_text.onnx`. The same task rewrites the tokenizer rules and the reference numbers the tests check against.
  - `ml/embedder/WordPieceTokenizer.kt`, `ml/embedder/BgeEmbedder.kt`, `VideoEmbedTexts.kt` (card EYKO-12, stage `embed_texts`): every caption (and every transcript chunk, once speech exists) becomes a `video_texts` row (`source`, `ref_id`, start and end time, text). The triggers keep the keyword index `video_texts_fts` in step, and each text gets a 384-number vector in `text_vec` from `BgeEmbedder` (BAAI/bge-small-en-v1.5, MIT, the Phase 1 embedder, as the ONNX file from its own repository; about 26 ms per caption on the Pixel). `WordPieceTokenizer` is that model's tokenizer in plain Kotlin, reading `assets/bge_vocab.txt`. The stage deletes the video's earlier texts and vectors first; a video with no transcript chunks is normal. Get the model with `task export-bge` (`src/benchmarks/export_bge.py`, 133 MB, also rewrites the vocabulary and the reference numbers) and push it: `adb push <file> /sdcard/Android/data/com.eykon.memory/files/models/bge_small_en_v1.5.onnx`. `VideoPipeline.STAGES` is now split, filter, dedup, scene, embed_images, embed_texts. The older `LocalEmbedder` / `TokenizerHelper.tokenize` pair is a stand-in that was never switched on; it is not used by this stage.
  - `VideoLink.kt` (card EYKO-14, stage `link`, the last one): a check, not a repair. `problems(db, videoId)` counts what must not exist for a video: kept frames without a picture hash, a scene record or an image vector; texts without a text vector; sound windows without a sound vector; frames, texts, sound segments, transcript chunks or sound windows timed outside the video (duration + 1 s); a recording time that cannot be read. `run` fails the job with those messages (for example "1 kept frames without an image vector"), which the Video tab then shows; it never changes data. `moment(recordedAt, tS)` gives the real clock time of a point in a video. `VideoPipeline.STAGES` is now split, filter, dedup, scene, embed_images, embed_texts, link.
  - `VideoJobs.requeueBehind` (called when the app starts): a video whose job finished before newer stages existed goes back in the queue and runs only the stages it has not done.
- `ui/screens/VideoScreen.kt` + `ui/viewmodels/VideoViewModel.kt`: The **📼 Video** tab: pick a clip from the gallery (system photo picker, no storage permission), confirmation line, a **Find a moment** box (type a phrase, get the closest frames as pictures with their time, likeness and stored caption), list of saved videos.
- `android/app/build.gradle.kts`: Gradle Kotlin DSL, `minSdk = 31`, `compileSdk = 35`, Room 2.6.1, KSP 2.0.21, Compose BOM 2024.10.00.

### Python Backend & Desktop Prototype (`src/`)
- `src/memories/`: 
  - `models.py`: Memory data schema (`MemoryRecord` with `metadata` support).
  - `database.py`: SQLite persistence, table schema, and `memories_fts` (FTS5) virtual table with sync triggers.
  - `repository.py`: CRUD operations for memory records (`save_memory`, `save_memories`, `get_all_memories`, `get_memory_by_id`).
  - `embedder.py`: Local `sentence-transformers` (`BAAI/bge-small-en-v1.5`, 512 tokens, 384-dim) wrapper with token helpers.
  - `service.py`: Text validation, token-bounded chunking (256 avg, 30-50 overlap, 400 ceiling), and `MemoryRecord` assembly.
  - `query.py`: Zero-latency static concept map for query expansion (bridges semantic gap for abstract questions).
  - `reranker.py`: Cross-encoder re-ranking model (`cross-encoder/ms-marco-MiniLM-L-6-v2`) for second-stage evaluation.
  - `search.py`: Three-stage retrieval pipeline:
    1. **Retrieval**: Fetches top 20 (`POOL_K`) candidates via semantic cosine similarity + top 20 via SQLite FTS5 BM25.
    2. **Fusion**: Combines lists using Reciprocal Rank Fusion (RRF).
    3. **Re-ranking**: Passes top 20 fused candidates to cross-encoder to compute deep semantic relevance against the original query, returning the final top 5. Emits `SearchResult` objects.
- `src/assistant/`: 
  - `prompt.py`: Factual RAG prompt formatting with strict anti-hallucination guard (`build_rag_prompt`).
  - `llm.py`: Google LiteRT-LM on-device edge engine (`litert-community/gemma-4-E2B-it-litert-lm`, 2.4 GB) with singleton caching (`generate_answer`).
  - `helpers.py`: Model health check utility (`check_model_available`, `get_model_status`).
- `src/ui/`:
  - `app.py`: Two-page Streamlit UI (📝 Add Memory · ❓ Ask Question). Startup model check, sample data loader, graceful error handling. Sidebar shows live memory count, model status, and demo tools. Retrieved memories display match badges (`⚡ Common`, `🧠 Semantic`, `🔤 BM25`), Semantic Cosine score, BM25 score, and Fused RRF score.
- `src/video_memory/` (cheap-model video pipeline, storage layer so far):
  - `schema.py`: Video memory tables in the same `data/memories.db` (`videos`, `frames`, `audio_segments`, `transcript_chunks`, `scene_records`, `video_texts` + `video_texts_fts`, `audio_windows`) and three vector tables (`image_vec` 512-d, `text_vec` 384-d, `audio_vec` 512-d). `init_db()` is idempotent; `delete_video()` removes a video and everything that belongs to it.
  - `db.py`: `connect()` (foreign keys on), `put_vector()` (float32 BLOB, size-checked) and `knn()` (loads a vector table into memory once, dot-product search). No SQLite extensions, so the same schema works on Android.
  - `models.py`: One dataclass per table.
  - `capture.py`: `save_upload()` checks the file type and size, stores the clip as `data/videos/<video_id>/<video_id>.<ext>`, reads recording time, duration and GPS with ffmpeg (`read_metadata()`), refuses files that hold no video, and adds the `videos` row. ffmpeg comes from the `imageio-ffmpeg` package, so nothing is installed by hand.
  - `repository.py`: `insert_video()`, `get_video()`.
- `src/ui/video_memory_page.py`: The **📼 Video memory** page (upload a clip; confirmation with recording time and length).
- `.streamlit/config.toml`: Streamlit's upload cap (500 MB), kept equal to `MEMORY_VIDEO_MAX_MB`.
- `src/config.py`: Central Pydantic settings (`BaseSettings` backed by `.env` with `MEMORY_` prefix). Video memory settings: `MEMORY_VIDEO_DIR` (`data/videos`), `MEMORY_VIDEO_IMAGE_DIM` (512), `MEMORY_VIDEO_TEXT_DIM` (384), `MEMORY_VIDEO_AUDIO_DIM` (512), `MEMORY_VIDEO_MAX_MB` (500), `MEMORY_VIDEO_TYPES` (`["mp4","mov","m4v","avi"]`). Perception settings: `MEMORY_DETECTOR_MODEL` (`models/yolox_tiny.onnx`), `MEMORY_DETECTOR_URL`, `MEMORY_DETECTOR_CONF` (0.35), `MEMORY_SCENE_PROMPT_MIN` (0.30), `MEMORY_SCENE_PLACES`, `MEMORY_SCENE_ACTIONS`; the phone keeps the same two numbers in `OptionA.kt`.
- `data/memories.db`: Local embedded SQLite database with FTS5 search index.

## Quick Start

### Prerequisites

#### For Phase 1 (Python / Desktop Prototype)
- **Python 3.10+**
- **[uv](https://github.com/astral-sh/uv)** (Python package & environment manager)
- *(Optional)* **[Task](https://taskfile.dev)** (`winget install Task.Task`) for one-line convenience commands (`task run`, `task test`, etc.). If not installed, you can use the direct `uv` commands listed below.

#### For Phase 2 (Android Native Client)
- **[Android Studio](https://developer.android.com/studio)** (recommended: automatically bundles JDK 17/21 and Android SDK)
- **Android SDK:** Platform API 31+ (Android 12+) required for on-device LiteRT-LM / Gemma 4 hardware acceleration.
- **Physical Device or Emulator:** Android 12+ (arm64 recommended for on-device LLM inference).

---

### Phase 1: Python Desktop Prototype

#### 1. Install Dependencies & Download Model
```bash
uv sync
task pull-model  # Or: uv run python -c "from huggingface_hub import hf_hub_download; from src.config import Settings; s = Settings(); hf_hub_download(s.LITERT_MODEL_REPO, s.LITERT_MODEL_FILE)"
```

#### 2. Run the Streamlit App
```bash
task run
# or directly:
uv run streamlit run src/ui/app.py
```
Opens in your browser at `http://localhost:8501`.  
- **📝 Add Memory** — paste any text; it's chunked, embedded, and stored in SQLite.  
- **❓ Ask Question** — hybrid search retrieves relevant memories, Gemma 4 generates a grounded answer on-device.

#### 3. Health & Pipeline Verification
```bash
task test-e2e     # One-command health check: DB, embedder, search, model
task test         # pytest suite in tests/ (temporary databases only, never data/memories.db)
task smoke        # One-line pipeline check against the real data/memories.db (was `task test`)
task check-config # Verify resolved settings
task check-video-db # Create the video memory tables if missing and list each with its row count
```

#### 4. Inspect SQLite Database
The database is stored locally at `data/memories.db`. You can view it with [DB Browser for SQLite](https://sqlitebrowser.org/) or the VS Code SQLite Viewer extension.

---

### Phase 2: Android Native App (`android/`)

#### 1. Open in Android Studio
1. Launch Android Studio.
2. Select **Open** and choose the `android/` directory (`FYP_Demo/android`).
3. Allow Gradle to sync dependencies (Room 2.6.1, Compose, Kotlin coroutines).
4. Click the green **Run (▶)** button to deploy to your connected Android 12+ device or emulator.

#### 2. Build & Test via Command Line
If running from terminal (requires `JAVA_HOME` pointing to JDK 17 or 21, e.g. Android Studio's bundled JBR):
```bash
cd android

# Run local JVM unit tests (TypeConverter serialization & TextCapture validation)
.\gradlew.bat test

# Build debug APK
.\gradlew.bat assembleDebug

# Run instrumented Room SQLite tests on connected device
.\gradlew.bat connectedAndroidTest
```

#### 3. Sideload Models to Device
The Gemma 4 model and ONNX models must be pushed directly to the app's external files directory to bypass SELinux restrictions on modern Android devices:
```bash
# Assuming device is connected via USB or Wi-Fi ADB
adb shell "mkdir -p /sdcard/Android/data/com.eykon.memory/files/models"

# Sideload Generation Model (LiteRT-LM)
adb push "models\gemma-4-E2B-it.litertlm" "/sdcard/Android/data/com.eykon.memory/files/models/"

# Sideload Embedding & Re-ranking Models (ONNX) - When provided
# adb push "models\bge-small-en-v1.5.onnx" "/sdcard/Android/data/com.eykon.memory/files/models/"
# adb push "models\ms-marco-MiniLM-L-6-v2.onnx" "/sdcard/Android/data/com.eykon.memory/files/models/"
```


## Troubleshooting

| Problem | Solution |
|---|---|
| **Model not found** error on startup | Run `task pull-model` to download Gemma 4 E2B (~2.4 GB). Requires internet. |
| **Embedding model download** hangs | First run downloads `BAAI/bge-small-en-v1.5` (~45 MB). Needs internet once; cached after. |
| **Port 8501 already in use** | Another Streamlit instance is running. Kill it or use `uv run streamlit run src/ui/app.py --server.port 8502`. |
| **Out of memory** during generation | Close other heavy apps. Gemma 4 E2B needs ~2-3 GB RAM. |
| **Slow first question** | The LLM engine loads on the first question (~10-30s). Subsequent questions are faster. |

## Demo Tips

1. **Quick setup:** Click the **🧪 Demo Tools** expander in the sidebar → **Load Sample Memories** to instantly populate 5 memories.
2. **Best demo questions:** "When is my dentist appointment?", "What is my brother's name?", "Do I prefer tea or coffee?"
3. **Show retrieval working:** After getting an answer, expand the **📚 Retrieved Memories** section to show the supervisor how semantic + BM25 hybrid search selects the right memories with scores.
4. **Show it's local:** Point out the sidebar shows "Local-first · On-device AI · No cloud" — no API keys, no internet needed after setup.
5. **Expected timings:** Adding a memory: ~1s. Searching: ~instant. LLM answer: 10-30s first time, ~5-15s after.

See [`PROJECT_SPEC.md`](PROJECT_SPEC.md) for the full specification and roadmap.
