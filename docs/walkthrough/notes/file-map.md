# File map: which stage documents which file

Authoritative scope for the Phase 1 stage deep dives. Written 22 October 2026
against commit `89b4da8` (branch `feature/video-memory`).

- **Primary** files get a full entry in that stage's §6 *File reference*
  (a level-3 heading holding the full repo-relative path in backticks, as
  in `stages/_TEMPLATE.md`) and appear in at least one node of that
  stage's JSON.
- **Also read** files belong to another stage. Mention them where they
  matter; give them a §6 entry only when this stage uses a part the owning
  stage does not cover (for example `VideoPipeline.kt` is owned by s01, but
  its `VideoFinish` object is documented by s07).
- **Data files** (assets, fixtures, golden JSON) are described in §2 / §5
  and in data-store nodes, not in §6.
- Always write full repo-relative paths in docs and JSON.

`A` below stands for `android/app/src/main/java/com/eykon/memory`,
`UT` for `android/app/src/test/java/com/eykon/memory`,
`AT` for `android/app/src/androidTest/java/com/eykon/memory`.
These abbreviations are only for this list. Expand them everywhere else.

---

## s01-intake: Video intake, schema & job queue (runtime, phone + laptop twin)

Primary:
- `A/MemoryApp.kt`
- `A/video/VideoCapture.kt`
- `A/video/VideoMetadata.kt`
- `A/video/VideoRepository.kt`
- `A/video/VideoSchema.kt`
- `A/video/VideoJobs.kt`
- `A/video/VideoWorker.kt`
- `A/video/VideoPipeline.kt` (`STAGES`, `VERSION`, `REDO_AFTER`, `redoAfter`; `VideoFinish` is s07)
- `A/data/MemoryDatabase.kt` (only the `onCreate` / `onOpen` hooks that create the video schema and turn on foreign keys; the rest is s09)
- `src/video_memory/__init__.py`
- `src/video_memory/capture.py`
- `src/video_memory/db.py` (`connect`; `put_vector` / `knn` are also covered by s06)
- `src/video_memory/models.py`
- `src/video_memory/repository.py`
- `src/video_memory/schema.py`
- `src/ui/video_memory_page.py`
- `src/config.py` (the `video_*` settings only)
- `.streamlit/config.toml`
- `tests/__init__.py`
- `tests/test_video_capture.py`
- `tests/test_video_schema.py`
- `UT/video/VideoMetadataTest.kt`
- `AT/video/VideoStorageTest.kt`
- `AT/video/VideoWorkerTest.kt`

Also read: `A/MainActivity.kt` (wiring, s09), `A/ui/viewmodels/VideoViewModel.kt` (s08), `Taskfile.yml` (`check-video-db`).

## s02-split: Split into frames and audio (runtime, phone)

Primary:
- `A/video/VideoSplit.kt`
- `A/video/FrameExtractor.kt`
- `A/video/AudioExtractor.kt`
- `A/video/MonoResampler.kt`
- `UT/video/VideoSplitMathTest.kt`
- `AT/video/VideoSplitTest.kt`

Data files: `android/app/src/androidTest/assets/test_clip.mp4`, `test_clip_repeat.mp4`, `test_clip_silent.mp4`, `test_clip_still.mp4`.
Also read: `src/benchmarks/ego4d_pipeline.py` (`split`, the laptop replica, s14).

## s03-keyframes: Keyframe selection, filter + dedup (runtime, phone)

Primary:
- `A/video/VideoFilter.kt`
- `A/video/FrameFilters.kt`
- `A/video/FrameHash.kt`
- `A/video/VideoDedup.kt`
- `A/ml/vision/ImageEmbedder.kt`
- `UT/video/FrameFiltersTest.kt`
- `UT/video/FrameHashTest.kt`
- `UT/video/TestPictures.kt`
- `AT/video/VideoFilterTest.kt`
- `AT/video/VideoDedupTest.kt`

Data files: `android/app/src/test/resources/filters/` (`blurred.png`, `dark.png`, `other.png`, `sharp.png`, `upright.png`, `golden.json`), `android/app/src/androidTest/assets/clip_golden.json`.
Also read: `src/benchmarks/filters_golden.py` (s12), `src/benchmarks/keyframe_tune.py` (s13), `docs/plans/keyframe-comparison-protocol.md`.

## s04-scene: Scene description, perception Option A (runtime, phone)

Primary:
- `A/video/VideoScene.kt`
- `A/video/OptionA.kt`
- `A/ml/vision/ObjectDetector.kt`
- `A/ml/vision/DfineDetector.kt`
- `A/ml/vision/ImagePrep.kt`
- `UT/video/OptionATest.kt`
- `UT/video/OptionASmoothTest.kt`
- `UT/video/VideoSceneCaptionTest.kt`
- `AT/video/VideoSceneTest.kt`

Data files: `android/app/src/main/assets/scene_prompts.json`, `android/app/src/main/assets/dfine_labels.json`, `android/app/src/test/resources/perception/dog.jpg`.
Also read: `src/config.py` (`detector_*`, `scene_*` settings), `src/benchmarks/perception_golden.py` (s12).

## s05-small-objects: Personal small objects, YOLOE-11L gated (runtime, phone)

Primary:
- `A/video/VideoSmallObjects.kt`
- `A/ml/vision/YoloeDetector.kt`
- `UT/video/SmallObjectsTest.kt`

Data files: `android/app/src/main/assets/yoloe_words.json`, the flag vectors in `android/app/src/main/assets/scene_prompts.json`.
Also read: `A/video/OptionA.kt` (`flags`, `flagged`, `FLAG_MIN`), `A/video/VideoScene.kt` (`buildCaption`, `PERSONAL`), `src/config.py` (`small_object_flags`, `small_object_flag_min`).

## s06-index: Vector & keyword indexing (runtime, phone)

Primary:
- `A/video/VideoEmbedImages.kt`
- `A/video/VideoEmbedTexts.kt`
- `A/video/VideoVectors.kt`
- `A/ml/embedder/BgeEmbedder.kt`
- `A/ml/embedder/WordPieceTokenizer.kt`
- `UT/video/VideoVectorsBlobTest.kt`
- `UT/ml/embedder/WordPieceTokenizerTest.kt`
- `AT/video/VideoEmbedImagesTest.kt`
- `AT/video/VideoEmbedTextsTest.kt`

Data files: `android/app/src/main/assets/bge_vocab.txt`, `android/app/src/test/resources/bge/tokens_golden.json`, `android/app/src/androidTest/assets/bge_golden.json`.
Also read: `src/video_memory/db.py` (`put_vector`, `knn`: the laptop twin of `VideoVectors`).

## s07-finalise: Integrity check, latest sightings, finish (runtime, phone)

Primary:
- `A/video/VideoLink.kt`
- `A/video/VideoLatest.kt`
- `A/video/VideoPipeline.kt` (the `VideoFinish` object only)
- `UT/video/VideoLatestCropTest.kt`
- `UT/video/VideoLinkMomentTest.kt`
- `AT/video/VideoLinkTest.kt`
- `AT/video/VideoLatestTest.kt`
- `AT/video/VideoFinishTest.kt`

Also read: `src/benchmarks/crop_pairs.py` and `AT/video/ObjectCropBenchmarkTest.kt` (s13, chose `CROP_COSINE_MIN`).

## s08-video-search: Moment search & the Video tab (runtime, phone)

Primary:
- `A/video/VideoSearch.kt`
- `A/video/SearchWindows.kt`
- `A/ml/vision/TextEmbedder.kt`
- `A/ml/vision/ClipTokenizer.kt`
- `A/ui/viewmodels/VideoViewModel.kt`
- `A/ui/screens/VideoScreen.kt`
- `UT/video/SearchWindowsTest.kt`
- `UT/ml/vision/ClipTokenizerTest.kt`
- `AT/video/VideoSearchTest.kt`

Data files: `android/app/src/main/assets/clip_bpe_merges.txt`, `android/app/src/test/resources/clip/tokens_golden.json`, `android/app/src/androidTest/assets/clip_text_golden.json`.
Also read: `A/video/VideoRepository.kt` (`listWithJobs`, s01), `A/MainActivity.kt` (wiring, s09), `src/benchmarks/ego4d_eval.py` (`windows`, s14).

## s09-phone-text-memory: Phone text memories & answers (runtime, phone)

Primary:
- `A/MainActivity.kt`
- `A/assistant/GenerationParams.kt`
- `A/assistant/LiteRTGenerator.kt`
- `A/assistant/ModelManager.kt`
- `A/assistant/PromptBuilder.kt`
- `A/capture/AudioCaptureService.kt`
- `A/capture/NativeSpeechRecognizer.kt`
- `A/capture/TextCaptureService.kt`
- `A/capture/WhisperTranscriber.kt`
- `A/data/Converters.kt`
- `A/data/MemoryDao.kt`
- `A/data/MemoryDatabase.kt`
- `A/data/MemoryRecord.kt`
- `A/ml/embedder/LocalEmbedder.kt`
- `A/ml/embedder/TokenizerHelper.kt`
- `A/ml/reranker/LocalCrossEncoder.kt`
- `A/retrieval/QueryExpander.kt`
- `A/retrieval/SearchService.kt`
- `A/ui/components/MemoryCountBadge.kt`
- `A/ui/components/RetrievedMemoryCard.kt`
- `A/ui/components/VoiceRecordButton.kt`
- `A/ui/navigation/AppNavigation.kt`
- `A/ui/screens/AddMemoryScreen.kt`
- `A/ui/screens/AskQuestionScreen.kt`
- `A/ui/screens/GenerationTestScreen.kt`
- `A/ui/theme/Color.kt`
- `A/ui/theme/Theme.kt`
- `A/ui/theme/Type.kt`
- `A/ui/viewmodels/AddMemoryViewModel.kt`
- `A/ui/viewmodels/AskQuestionViewModel.kt`
- `A/ui/viewmodels/GenerationTestViewModel.kt`
- `android/app/src/main/AndroidManifest.xml`
- `android/app/src/main/res/values/strings.xml`
- `android/app/src/main/res/values/themes.xml`
- `android/app/src/main/res/xml/backup_rules.xml`
- `android/app/src/main/res/xml/data_extraction_rules.xml`
- `UT/assistant/PromptBuilderTest.kt`
- `UT/capture/AudioCaptureTest.kt`
- `UT/capture/TextCaptureServiceTest.kt`
- `UT/data/ConvertersTest.kt`
- `UT/retrieval/SearchServiceTest.kt`
- `UT/ui/viewmodels/AddMemoryViewModelTest.kt`
- `UT/ui/viewmodels/AskQuestionViewModelTest.kt`
- `AT/data/MemoryDaoTest.kt`

Also read: `scratch/litertlm/` (vendored LiteRT-LM AAR extract; check whether the build uses it).

## s10-laptop-text-rag: Laptop text RAG, Phase 1 (runtime, laptop)

Primary:
- `main.py`
- `src/__init__.py`
- `src/config.py` (RAG, LiteRT and Ollama settings)
- `src/memories/__init__.py`
- `src/memories/database.py`
- `src/memories/embedder.py`
- `src/memories/models.py`
- `src/memories/query.py`
- `src/memories/repository.py`
- `src/memories/reranker.py`
- `src/memories/search.py`
- `src/memories/service.py` (text chunking; `create_memories_from_video` is s11)
- `src/assistant/__init__.py`
- `src/assistant/helpers.py`
- `src/assistant/llm.py`
- `src/assistant/prompt.py`
- `src/ui/__init__.py`
- `src/ui/app.py` (sidebar, Add Memory and Ask Question pages)
- `tests/test_smoke.py`
- `.env.example`

Also read: `Taskfile.yml` (`run`, `install`, `pull-model`, `smoke`, `test-e2e`, `check-config`).

## s11-laptop-vlm-video: Laptop VLM video captioning, Option C reference (runtime, laptop)

Primary:
- `src/vision/__init__.py`
- `src/vision/extractor.py`
- `src/vision/captioner.py`
- `src/vision/processor.py`
- `src/memories/service.py` (`create_memories_from_video` only)
- `src/ui/app.py` (the Process Video page only)
- `check_vlm_env.py`
- `test_litert_vision.py`

Also read: `src/config.py` (`VLM_*`, `FRAME_INTERVAL_SECONDS`, `CAPTION_*`), `Taskfile.yml` (`pull-vlm`, `check-vlm`, `test-vision-integration`).

## s12-export-parity: Model export & phone-parity files (offline, laptop to phone)

Primary:
- `src/benchmarks/export_clip.py`
- `src/benchmarks/export_clip_text.py`
- `src/benchmarks/export_bge.py`
- `src/benchmarks/perception_golden.py`
- `src/benchmarks/phone_detector_assets.py`
- `src/benchmarks/filters_golden.py`
- `AT/video/DetectorGoldenTest.kt`
- `AT/video/OptionAPhoneTest.kt`

Data files written: `android/app/src/main/assets/` (`scene_prompts.json`, `clip_bpe_merges.txt`, `bge_vocab.txt`, `dfine_labels.json`, `yoloe_words.json`), `android/app/src/test/resources/` (`filters/golden.json`, `bge/tokens_golden.json`, `clip/tokens_golden.json`), `android/app/src/androidTest/assets/` (`bge_golden.json`, `clip_golden.json`, `clip_text_golden.json`, `detector_golden.json`, `detector_golden.jpg`, `perception_golden.json`).
Also read: `src/benchmarks/yoloe_phone.py` and `src/benchmarks/hybrid_phone.py` (their `inputs` modes export models, s13), `Taskfile.yml` (`export-clip`, `export-clip-text`, `export-bge`, `pull-detector`, `golden-perception`, `golden-filters`, `phone-detector-assets`).

## s13-component-benchmarks: Component benchmarks (offline, laptop + phone)

Primary:
- `src/benchmarks/keyframe_eval.py`
- `src/benchmarks/keyframe_tune.py`
- `src/benchmarks/keyframe_public.py`
- `src/benchmarks/keyframe_motion.py`
- `src/benchmarks/detector_bench.py`
- `src/benchmarks/detector_hybrid.py`
- `src/benchmarks/hybrid_phone.py`
- `src/benchmarks/yoloe_phone.py`
- `src/benchmarks/vlm_bench.py`
- `src/benchmarks/vlm_models.py`
- `src/benchmarks/perception_score.py`
- `src/benchmarks/frame_search_probe.py`
- `src/benchmarks/small_objects_eval.py`
- `src/benchmarks/crop_pairs.py`
- `src/benchmarks/vector_storage_spike.py`
- `AT/video/KeyframeBenchmarkTest.kt`
- `AT/video/PerceptionBenchmarkTest.kt`
- `AT/video/OwlPhoneBenchmarkTest.kt`
- `AT/video/HybridPhoneBenchmarkTest.kt`
- `AT/video/YoloePhoneBenchmarkTest.kt`
- `AT/video/ObjectCropBenchmarkTest.kt`
- `AT/spike/VectorStorageSpikeTest.kt`

Data files: `docs/results/` dated `2026-10-12` to `2026-10-14` and the folders `keyframes/`, `perception/`, `detectors/`, `vlm/`, `small-objects/`, `latest/`, `screens/`.
Also read: `docs/plans/keyframe-comparison-protocol.md`, `Taskfile.yml` (the matching tasks).

## s14-ego4d-eval: Ego4D episodic-memory evaluation (offline, laptop)

Primary:
- `src/benchmarks/ego4d_select.py`
- `src/benchmarks/ego4d_pipeline.py`
- `src/benchmarks/ego4d_eval.py`
- `src/benchmarks/ego4d_actions.py`
- `src/benchmarks/ego4d_hybrid.py`
- `src/benchmarks/ego4d_lastseen.py`
- `src/benchmarks/ego4d_gate.py`
- `src/benchmarks/ego4d_phone_compare.py`

Data files: `docs/results/2026-10-19-ego4d-subset.md`, `docs/results/2026-10-20-ego4d-baseline.md`, `docs/results/2026-10-21-ego4d-improvements.md`, `docs/results/ego4d/`.

## s15-legacy-benchmarks: Phase 1/3 benchmarks & device scripts (offline, laptop + adb)

Primary:
- `src/benchmarks/__init__.py`
- `src/benchmarks/run.py`
- `src/benchmarks/data.py`
- `src/benchmarks/metrics.py`
- `src/benchmarks/experiments.py`
- `src/benchmarks/experiment_a1.py`
- `src/benchmarks/cross_pipeline.py`
- `src/benchmarks/_captioners.py`
- `src/benchmarks/vision_bench.py`
- `src/benchmarks/soak_test.py`
- `scratch/endurance_stress_test.py`
- `scratch/endurance_test_infinix.py`
- `scratch/generate_comparison_graphs.py`
- `scratch/generate_report.py`
- `scratch/inspect_ui.py`
- `scratch/profile_device_kpis.py`
- `scratch/sync_db_infinix.py`

Also read: `Taskfile.yml` (`benchmark`, `benchmark-vision`, `experiment`, `experiment-a5`, `experiment-a6`).

## Not in any stage: covered by the cross-cutting docs

- Build and tooling (`04-data-and-config.md`): `pyproject.toml`, `.python-version`, `Taskfile.yml` (all tasks), `.mcp.json`, `android/build.gradle.kts`, `android/app/build.gradle.kts`, `android/settings.gradle.kts`, `android/gradle.properties`, `android/gradle/wrapper/gradle-wrapper.properties`, `android/app/proguard-rules.pro`, `android/.gitignore`, `.gitignore`.
- Skipped entirely: see `00-overview.md` §3.11.

---

## Shared node ids (use these exact ids; do not redefine them)

Physical data stores that several stages read or write are defined **once**, by
the owning stage below. Other stages point their edges at these ids and must
not create duplicates. Models and algorithms are different: each stage gets
its own node for each model it runs, with a shared `key` so the instances can
be grouped (for example every MobileCLIP image-encoder node has
`"key": "mobileclip-s2-image"`).

| Node id | What it is | Defined in |
|---|---|---|
| `s01-intake/file-video` | the copied clip, `files/videos/<video_id>/<video_id>.<ext>` | s01 |
| `s01-intake/db-videos` | `videos` table | s01 |
| `s01-intake/db-jobs` | `jobs` table (phone only) | s01 |
| `s01-intake/db-frames` | `frames` table | s01 |
| `s01-intake/db-audio-segments` | `audio_segments` table | s01 |
| `s01-intake/db-transcript-chunks` | `transcript_chunks` table | s01 |
| `s01-intake/db-scene-records` | `scene_records` table | s01 |
| `s01-intake/db-video-texts` | `video_texts` table | s01 |
| `s01-intake/db-video-texts-fts` | `video_texts_fts` keyword index (fts4 on the phone, FTS5 on the laptop) | s01 |
| `s01-intake/db-audio-windows` | `audio_windows` table | s01 |
| `s01-intake/db-image-vec` | `image_vec` table (512 float32 BLOB) | s01 |
| `s01-intake/db-text-vec` | `text_vec` table (384 float32 BLOB) | s01 |
| `s01-intake/db-audio-vec` | `audio_vec` table (512 float32 BLOB) | s01 |
| `s01-intake/db-object-sightings` | `object_sightings` table | s01 |
| `s02-split/file-frames` | the frame JPEGs of one video | s02 |
| `s02-split/file-audio-wav` | `audio16k.wav` | s02 |
| `s03-keyframes/file-clip-vectors` | `clip_vectors.bin` | s03 |
| `s09-phone-text-memory/db-memories` | phone `memories` table and its fts4 index (Room) | s09 |
| `s10-laptop-text-rag/db-memories` | laptop `memories` table and `memories_fts` (FTS5) in `data/memories.db` | s10 |
| `s12-export-parity/asset-scene-prompts` | `android/app/src/main/assets/scene_prompts.json` | s12 |
| `s12-export-parity/asset-clip-merges` | `android/app/src/main/assets/clip_bpe_merges.txt` | s12 |
| `s12-export-parity/asset-bge-vocab` | `android/app/src/main/assets/bge_vocab.txt` | s12 |
| `s12-export-parity/asset-dfine-labels` | `android/app/src/main/assets/dfine_labels.json` | s12 |
| `s12-export-parity/asset-yoloe-words` | `android/app/src/main/assets/yoloe_words.json` | s12 |
| `s12-export-parity/onnx-mobileclip-image` | `mobileclip_s2_image.onnx` in the phone's models folder | s12 |
| `s12-export-parity/onnx-mobileclip-text` | `mobileclip_s2_text.onnx` | s12 |
| `s12-export-parity/onnx-bge-small` | `bge_small_en_v1.5.onnx` | s12 |
| `s12-export-parity/onnx-yolox-tiny` | `yolox_tiny.onnx` | s12 |
| `s12-export-parity/onnx-dfine-s` | `dfine_s_obj365.onnx` | s12 |
| `s12-export-parity/onnx-yoloe-11l` | `yoloe_11l_own.onnx` | s12 |
| `s12-export-parity/file-gemma-litertlm` | `gemma-4-E2B-it.litertlm` (fetched by `task pull-model`) | s12 |
| `s14-ego4d-eval/ext-ego4d` | Ego4D episodic-memory validation subset, `D:/eykon-cache/ego4d` | s14 |
| `s13-component-benchmarks/ext-own-clips` | the team's own recorded clips and hand labels | s13 |
| `s13-component-benchmarks/ext-epic-kitchens` | EPIC-KITCHENS-100 subset | s13 |
