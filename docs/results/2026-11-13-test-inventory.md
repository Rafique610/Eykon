# Test inventory: how many tests, what they cover, and one saved log (EYKO-91 step 9, Head 2 C5)

**Date:** 13 November 2026 · **By:** Taha Ahmed (lead) · **Card:** EYKO-91 · **Commit:** 060a7dd (`taha/eyko-91-vectors-laptop-v2`,
with `feature/video-memory` @ 930af2d merged in) · **Supervisor question C5:** "You say the tests pass. How many, and what do they cover?"

## Answer

| Side | Tests | Ran today | Result | Coverage |
|---|---|---|---|---|
| Laptop, pytest (`tests/`) | **30** in 5 files | yes, this laptop | **30 passed** in 17.6 s | **9 %** of `src/` overall; **93 %** of `src/video_memory` (the code the phone copies), 26 % of `src/memories`, 4 % of `src/benchmarks` |
| Phone, JVM unit tests (`android/app/src/test`) | **119** in 23 classes | yes, on Rafique's laptop (13 Nov, this branch) | **119 passed** in 2.4 s (`docs/results/test-inventory/phone-jvm-2026-11-13.txt`) | not measured |
| Phone, on-device tests (`android/app/src/androidTest`) | **133** in 31 classes | no: needs a phone (Rafique holds the A32 and Pixel) | — | not measured |
| CI | none | — | there is no `.github/workflows` or other CI in the repo | — |

At the 2 Nov gap review the counts were 109 JVM and 104 on-device. The 9 % overall is low because `src/benchmarks`
(4,111 of 5,207 statements) holds one-off measurement scripts that are not unit-tested by design; their results are
checked against raw logs in each result file instead. `src/assistant` (the laptop LLM answer) has no tests (0 %).

## Laptop: what was run

```
uv run --no-project --python 3.10 --index https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match \
  --with torch --with sentence-transformers --with pytest --with pytest-cov --with numpy==2.2.6 --with pydantic-settings \
  --with imageio-ffmpeg --with pillow --with psutil==7.2.2 --with sqlite-vec==0.1.9 --with usearch==2.26.5 \
  pytest -v --cov=src --cov-report=term tests/
```

This is `task test` (`uv run pytest -q`) in a small environment: the full project would also install llama-cpp-python
(compiled), streamlit and ollama, which no test imports. Full log with the coverage table:
[`test-inventory/laptop-2026-11-13-pytest.txt`](test-inventory/laptop-2026-11-13-pytest.txt) (home paths replaced by `<repo>`).

| File | Tests | What it covers |
|---|---|---|
| `test_schema_parity.py` | 4 | the laptop's and the phone's table designs are identical: tables, columns, keys, foreign keys, indexes, keyword index (C1) |
| `test_smoke.py` | 2 | settings point at the memories database; creating the database twice changes nothing |
| `test_vector_recall.py` | 12 | recall@20 with ties (the benchmark's own check), the S1/S2/S3 vector sources, EPIC frame picking and streamed reads with retries (EYKO-91) |
| `test_video_capture.py` | 5 | reading a real clip's metadata; saving an upload; wrong type, renamed text and too-big files are refused and leave nothing |
| `test_video_schema.py` | 7 | video tables: idempotent setup, a frame needs its video, vectors stored and searched, wrong size refused, keyword search, delete leaves nothing |

## Phone: what exists (counted from the source, `@Test` per class)

To run them: `cd android && ./gradlew testDebugUnitTest` (JVM). On-device: **never `connectedDebugAndroidTest`** (it uninstalls the app and
deletes its memories and models, `docs/invariants/tooling.md`); install both APKs with `adb install -r`, then
`adb shell am instrument -w -e class <class> com.eykon.memory.test/androidx.test.runner.AndroidJUnitRunner`. Several on-device classes need model files or kit clips on the phone, as their own comments say,
and the benchmark and route classes are measurements, not pass/fail checks. Only single-test logs are saved so far
(for example `docs/results/vectors/bgkill/*/instrument-output.txt`); the JVM suite has a full log (above, 13 Nov); **no full on-device log exists yet.**

**JVM unit tests (119)**

| Class | Tests | What it covers |
|---|---|---|
| `PromptBuilderTest` | 4 | the answer prompt: with and without memories, generation settings, cleaning the answer |
| `AudioCaptureTest` | 2 | WAV header constants; a memory made from transcribed audio |
| `TextCaptureServiceTest` | 4 | typed text becomes a memory; empty or blank input is refused |
| `ConvertersTest` | 4 | embedding list to JSON and back; empty, blank and broken JSON |
| `WordPieceTokenizerTest` | 4 | The Kotlin tokenizer against the laptop's bge-small tokenizer: tokens_golden.json holds the |
| `ClipTokenizerTest` | 4 | The Kotlin tokenizer against open_clip's own tokenizer: tokens_golden.json holds the numbers |
| `SearchServiceTest` | 4 | text-memory search: empty database, ranking, expanded concepts, punctuation |
| `AddMemoryViewModelTest` | 2 | saving a memory from the screen; empty input refused |
| `AskQuestionViewModelTest` | 5 | question screen state: typing, blank refused, answer built, speech auto-submit |
| `FrameFiltersTest` | 16 | Noise with every second column copied from its neighbour: clearly less sharp than plain noise. |
| `FrameHashTest` | 6 | the frame hash matches OpenCV's on every test picture and pair |
| `OptionASmoothTest` | 4 | Cards EYKO-60 (action smoothing) and EYKO-63 (which frames YOLOE looks at). |
| `OptionATest` | 9 | The plain maths of perception Option A. The models themselves are tested on a phone (OptionAPhoneTest). |
| `SearchWindowsTest` | 3 | Card EYKO-58: the same window rule as src/benchmarks/ego4d_eval.py `windows` (grow 0.85, gap 10 s, +-1.5 s). |
| `SmallObjectsTest` | 10 | The plain maths of D-FINE, YOLOE and the "small_objects" stage (card EYKO-32). The models run in DetectorGoldenTest on a phone. |
| `VideoCopyTest` | 7 | EYKO-71: the hash taken while copying, and the refusals when the file is too big or the phone too full. |
| `VideoLatestCropTest` | 5 | Which square part of the picture stands for an object's box. |
| `VideoLinkMomentTest` | 3 | The clock time of a point in a video is the recording time plus the seconds into it. |
| `VideoMetadataTest` | 7 | location (ISO 6709) and recording time read from the video; broken values are null |
| `VideoSceneCaptionTest` | 6 | The caption is plain words built from the fields. No model is involved. |
| `VideoSplitMathTest` | 5 | Upward zero crossings per second: the tone's frequency if the output rate is right. |
| `VideoVectorsBlobTest` | 2 | A stored vector must be the same bytes the laptop's numpy writes: float32, little-endian. |
| `VideoVectorsRankTest` | 3 | EYKO-102: the faster ranking and dot product give the same answers as the plain ones they replaced. |

**On-device tests (133)**

| Class | Tests | What it covers |
|---|---|---|
| `MemoryDaoTest` | 4 | Room DAO of the text memories: insert, get, order by time, delete, count |
| `RouteR1Test` | 2 | EYKO-105, route R1 (throwaway): sqlite-vec loaded into Google's bundled SQLite |
| `RouteR2DiagnoseTest` | 1 | EYKO-106: why is requery (R2) about 2x slower than Google's bundled SQLite (R1) at the same vec0 search? |
| `RouteR2Test` | 2 | EYKO-106, route R2 (throwaway): sqlite-vec loaded into requery's SQLite (sqlite-android 3.49.0, |
| `RouteR4StaticTest` | 6 | EYKO-108 (route R4, throwaway): our own NDK build of SQLite with sqlite-vec compiled in, opened |
| `VectorStorageSpikeTest` | 3 | EYKO-31 spike (throwaway): can the phone's SQLite use sqlite-vec, and how fast is the |
| `DetectorGoldenTest` | 2 | D-FINE and YOLOE with the real files on this phone, the picture prepared by the app's own code, |
| `HybridPhoneBenchmarkTest` | 1 | Card EYKO-32, the mixed detectors on the phone: D-FINE S (Objects365) and the 8-bit OWLv2 on all 50 |
| `KeyframeBenchmarkTest` | 1 | Card EYKO-45, the phone half: for every clip in the app's files/eval_clips folder, run |
| `ObjectCropBenchmarkTest` | 1 | Card EYKO-15, the data for choosing the crop threshold: every clip in files/eval_clips goes |
| `OffHeapVectorTest` | 5 | EYKO-109 (O1): keep the vectors outside the Java heap and/or smaller. Runs the app's own |
| `OptionAPhoneTest` | 3 | Perception Option A with the real models on this phone, against what the laptop got for the |
| `OwlPhoneBenchmarkTest` | 1 | Laptop-first follow-up to docs/results/2026-10-14-detectors-open-vocabulary.md: how long the 8-bit |
| `PerceptionBenchmarkTest` | 1 | Card EYKO-9, the measurement: every clip in files/eval_clips goes through the app's own stages |
| `VideoCaptureTest` | 4 | Card EYKO-71: the same file added twice gives one row and a message; a different file still works; a file over the |
| `VideoDedupTest` | 7 | The dedup stage on a real phone. test_clip_repeat.mp4 shows picture A for 1 s, picture B for |
| `VideoEmbedImagesTest` | 8 | The embed_images stage and vector search on a real phone. The test named |
| `VideoEmbedTextsTest` | 9 | The embed_texts stage on a real phone. Tests named "...WithTheRealModel(s)" need the model |
| `VideoFilterTest` | 5 | The filter stage on a real phone. test_clip_still.mp4 is 5 s of one unchanging picture; |
| `VideoFinishTest` | 8 | Card EYKO-16: a job that gets through every stage leaves its video ready to search; one that |
| `VideoLatestTest` | 13 | The latest stage on a real phone. In the rule tests a stand-in replaces the model: an |
| `VideoLinkTest` | 7 | The link stage on a real phone. Every test works on its own throw-away database, never the |
| `VideoRerunSafetyTest` | 4 | Card EYKO-119, supervisor question C1: "does a resumed stage give the same rows as a clean run?" |
| `VideoSceneTest` | 8 | The scene stage on a real phone. Tests named "...WithTheRealModels" need yolox_tiny.onnx and |
| `VideoSearchSpeedTest` | 1 | EYKO-102: how long the app's own search (VideoSearch.frames) takes on this phone, end to end, |
| `VideoSearchTest` | 6 | Search by typed phrase over stored frame vectors, on a real phone. Tests named |
| `VideoSplitTest` | 4 | The split stage on a real phone, with two 10 s clips made by ffmpeg (640x360, 30 fps): |
| `VideoStorageTest` | 4 | The video tables and the repository, on the phone's own SQLite, in an in-memory database. |
| `VideoWorkerTest` | 10 | The job queue and worker on the phone's own SQLite, with stages made up in each test. |
| `YoloePfPhoneBenchmarkTest` | 1 | Card EYKO-64: what YOLOE-11S prompt-free (AGPL-3.0, academic use) costs on the Pixel, on the kept frames of the two kit |
| `YoloePhoneBenchmarkTest` | 1 | Card EYKO-32: YOLOE-11L (AGPL-3.0, academic use) with its word list fixed to six own phrases, on all |

## Not done

- **A full phone-side log** (both JVM and on-device) and a phone coverage figure. JVM tests need the Android SDK on this
  laptop (Java 11 here; the build needs 17); on-device tests need a phone. Whoever holds a phone can run the two Gradle
  commands above and save the output next to the laptop log.
- **CI.** None is set up, so there is no CI log to link.
