# Persistent Memory App

A local-first personal memory app. Store details about your life (notes, facts, events, preferences), and query them using natural-language questions with locally-grounded retrieval-augmented generation (RAG).

> ✅ **Status:** Phase 1 Complete (End-to-End Pipeline) + Phase 1.1 Complete (Retrieval Quality Improvements).  
> 🔄 **Phase 2 In Progress:** Step 01, Step 02, Step 03 & Step 04 Complete (Android Project Setup + Storage + Capture + LiteRT-LM + FTS5 & ONNX Semantic Search).
> 🔄 **Phase 3 In Progress:** Step 01, Step 02, & Step 03 Complete (Literature Review, Environment Setup, & Frame Extraction).
> - Hybrid search Hit@5: **93.3%**
> - Exact factual questions Hit@1: **100%**
> - Android Target: **API 31 (Android 12)+** for Gemma 4 / LiteRT-LM

## Architecture

Built using a **feature-based file structure**:

### Android Core & Assistant (`android/`)
- `android/app/src/main/java/com/eykon/memory/data/`:
  - `MemoryRecord.kt`: Room SQLite entity mirroring the Phase 1 schema (`id`, `text`, `embedding`, `timestamp`, `source_type`, `metadata`).
  - `Converters.kt`: Room TypeConverter serializing `List<Float>` ↔ SQLite TEXT (JSON string) for the 384-dim vector.
  - `MemoryDao.kt`: Suspend CRUD methods (`insert`, `insertAll`, `getAll`, `getById`, `deleteById`, `count`, `deleteAll`) + `getAllAsFlow()`.
  - `MemoryDatabase.kt`: Room SQLite database singleton (`memories.db`).
- `android/app/src/main/java/com/eykon/memory/capture/`:
  - `TextCaptureService.kt`: Input validation (empty/whitespace guard) and `MemoryRecord` assembly.
- `android/app/src/main/java/com/eykon/memory/assistant/`:
  - `PromptBuilder.kt`: Formats grounded RAG prompt with Phase 1 parity (7 strict guidelines + 5 few-shot examples).
  - `GenerationParams.kt`: Generation hyperparameters (`temperature: 0.3f`, `maxOutputTokens: 256`, `topK: 40`, `topP: 0.95`).
  - `ModelManager.kt`: Resolves path to `gemma-4-E2B-it.litertlm` and provides target ADB sideload instructions.
  - `LiteRTGenerator.kt`: On-device inference runner with background dispatch (`Dispatchers.Default`) and answer prefix cleaner.
- `android/app/src/main/java/com/eykon/memory/ui/`:
  - `screens/AddMemoryScreen.kt`: Jetpack Compose screen for text capture and live recent memories list.
  - `screens/GenerationTestScreen.kt`: Compose test harness for on-device LLM generation with latency metrics and full prompt inspector.
  - `viewmodels/AddMemoryViewModel.kt`: Compose ViewModel managing `AddMemoryUiState` and Room StateFlow.
  - `viewmodels/GenerationTestViewModel.kt`: Compose ViewModel managing generation test state.
  - `theme/`: Material 3 theme (Color, Typography, Theme).
- `android/app/src/main/java/com/eykon/memory/`:
  - `MemoryApp.kt`: Application class managing lazy database singleton.
  - `MainActivity.kt`: Entry activity hosting tabbed navigation between Text Capture and Gemma Generation.
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
- `src/config.py`: Central Pydantic settings (`BaseSettings` backed by `.env` with `MEMORY_` prefix).
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
task test         # Full pipeline test
task check-config # Verify resolved settings
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
