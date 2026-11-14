# EYKO-119: are the ten stages safe to run again, and which failures must not be retried (Head 3, C1 and C2)

11 November 2026. Code read, tests written and run on the Pixel 9 Pro XL, and the app force-stopped inside three stages on the Pixel with the real models (section "Real force-stop on the Pixel").

## Short answer

**C1: yes, they already were.** Reading all ten stages showed each one removes or rebuilds its own rows before writing, as `VideoPipeline.kt` has required since the start. What was missing was proof, so this card adds it (`VideoRerunSafetyTest`). It found nothing to fix in the stages. **C2: no, it wasted attempts.** Every error was retried three times, even ones that cannot succeed. Two real cases are now failed on the first attempt.

## What each stage writes and what happens when it runs again

| Stage | Writes | When it runs again | Safe |
|---|---|---|---|
| split | `frames` rows, `frames/*.jpg`, `audio16k.wav` | Deletes this video's `frames` rows first (foreign keys remove anything hanging on them), wipes and remakes the frames folder, writes the WAV again | Yes |
| filter | `frames.kept`, `drop_reason` | Sets every frame back to kept, then decides again, all in one transaction | Yes |
| dedup | `frames.phash`, `kept`/`drop_reason` ("duplicate of frame N"), `clip_vectors.bin` | First un-drops the frames this stage dropped, then decides again; the vector file is rewritten whole | Yes |
| scene | `scene_records` | Deletes this video's records and inserts the new ones in one transaction | Yes |
| small_objects | `scene_records.objects` and `caption`, **updated in place** | Removes its own earlier finds (source `own`/`owl`) from each record, then adds this run's | Yes, and it is the one that depends on that filter (see the planted-bug check below) |
| embed_images | `image_vec` | Deletes this video's vectors and inserts again in one transaction; drops the vector file so it is rebuilt at the next search | Yes |
| embed_texts | `video_texts`, `text_vec` | Deletes both, inserts again in one transaction | Yes |
| link | nothing (it only reads) | Same check again | Yes |
| latest | `object_sightings`, and `is_latest`/`superseded_by` of the same labels in other videos | Deletes this video's sightings, inserts, then recomputes every affected label from all videos, in one transaction | Yes |
| finish | `videos.status`, deletes dropped frames' files | Marks ready again; deleting already-deleted files counts 0 | Yes |

Two things that looked risky and are not: the dedup vector file is written without a temporary name, so a kill during the write leaves a short file, but the file is only read by later stages and the job only reaches them after dedup is saved as done, and a rerun of dedup overwrites it. The dedup "un-drop" step runs outside the transaction; a kill after it and before the transaction leaves frames kept with no reason, and the rerun decides again.

## Tests (new `VideoRerunSafetyTest`, real stages on the phone's SQLite, stand-ins for the models)

The reference is a clean run of all ten stages on `test_clip_repeat.mp4`. The comparison covers every table, every vector (as hex), the files in the video's folder and the video's status.

| Check | Result on the Pixel |
|---|---|
| The reference run reaches ready with rows in frames, scene, texts, image vectors, text vectors and sightings (so the comparisons are not empty) | pass |
| Each of the 10 stages run twice in a row (the app died after the stage wrote its rows, before the job saved "done") gives the reference result | pass, 10 of 10 |
| A stage that dies half-way (an exception on the second model call) and then runs again gives the reference result: dedup, scene, small_objects, embed_texts, latest | pass, 5 of 5 (each one confirmed to have crashed) |
| split after an earlier half-finished run left a stray picture, a stray WAV and a stray `frames` row | pass |
| **Planted bug:** small_objects without its "remove my earlier finds" line | the run-twice test **fails** on "stage small_objects run twice", so the test can see this kind of fault. The line was put back; `git diff` of the file is empty. |

embed_images is not in the half-way list because it reuses dedup's saved vectors and never calls its model on this clip.

## C2: failures that must not be retried

| Change | Detail |
|---|---|
| `PermanentFailure` (new, `VideoPipeline.kt`) | Extends `IllegalStateException`. The worker gives it one attempt: the job is failed at once with the reason, the video is marked failed. All other errors keep 3 attempts. |
| split | "no frame could be read from the video" (both decoding ways ran and gave nothing) is a `PermanentFailure` |
| link | Broken rows found by the check are a `PermanentFailure`: the check repairs nothing, so a second run finds the same rows. The stored text now starts "PermanentFailure: ..." instead of "IllegalStateException: ..." |

Tests: `VideoWorkerTest` (2 new): a permanent failure ends with 1 attempt, 1 call, the reason kept, the stages after it not run, the video failed; Retry starts again at the failed stage and fails at once again. `VideoLinkTest` updated for the new text and checks 1 attempt.

Pixel run, 33 tests: VideoRerunSafetyTest 4, VideoWorkerTest 10, VideoLinkTest 7, VideoSplitTest 4, VideoFinishTest 8, all pass. Laptop JVM suite: 119 of 119.

## Real force-stop on the Pixel (real models, the app's own picker)

Pixel 9 Pro XL, on the charger, app in front, build `a3ea313` plus this card. One kit clip (`PXL_20261014_094359202`, 74.5 s, 186 MB). The EYKO-71 duplicate check refuses the same bytes twice, so four copies of the clip were used, each with 8, 16 or 24 empty bytes (`free` atoms) added at the end: a different fingerprint, the same frames. The four added with the app's own Video tab picker. `scripts/eyko119_force_stop.py` waited for the app's own `copy` log line, force-stopped the app (`am force-stop`) a set time after the log line of the stage before the one to hit, read the job's saved stage from the pulled database, reopened the app, and waited for `finish ... ready`. Before the test the app's database and vector files were backed up; afterwards they were put back and compared byte for byte (identical), the four test videos' folders and the four clips in Downloads were removed, and the app opened without a crash.

| Run | Killed | Database at the kill | Resumed at | Ready | Link counts |
|---|---|---|---|---|---|
| C0 (clean) | no | | | yes | all 0 |
| K1 | in `split`, 3 s after the copy | saved stage empty, job running, **0 frames** (split had deleted its old rows and not yet written the new) | `split`, all ten stages | yes | all 0 |
| K2 | in `scene`, 2 s after `dedup` | saved `dedup`, 224 frames, 0 scene records | `scene`, then the rest | yes | all 0 |
| K3 | in `latest`, 4 s after `link` | saved `link`, 10 scene records and texts, **0 sightings** (latest had not committed) | `latest`, `finish` | yes | all 0 |

Every killed run ended with exactly the clean run's numbers: 224 frames, 10 kept, 10 scene records, 10 texts, 10 image vectors, 10 text vectors, 54 sightings of which 30 latest, and the same captions fingerprint (`f83b795c...`, a hash of all captions in frame order). Job attempts stayed 0 in every run: a force-stop is not counted as a failure. Each killed run had 2 processes (the killed one and the resumed one). The numbers, link counts and logcat of each run are in `docs/results/eyko119/` (`*.json`, `*-logcat.txt`); `python scripts/eyko119_force_stop.py compare --out docs/results/eyko119` prints the table.

Together with Zara's 9 Infinix kills (EYKO-116, Part 3: scene, small_objects, embed_texts), `split`, `scene` and `latest` are now killed on a phone with the real models, and `small_objects` and `embed_texts` too. Not killed on a phone: `filter` (about 0.6 s), `dedup` (3 s), `embed_images` (40 ms), `link` (instant) and `finish`; those are covered by the run-twice tests above.

Limits: a clean `force-stop`, not a power-manager or memory kill; one clip, one phone; the kill time is a delay after a log line, so it lands inside the stage but not at a chosen instant (the K1 and K3 databases show the kills hit before the stage's own commit, the case that matters).

## Not done, and why

- **Only two errors are classed permanent.** Which other errors a bad file produces (HEVC with no decoder, a truncated file, no audio track) is what EYKO-118 and EYKO-123 will show. Classing errors before seeing them would be a guess; extend this when that table exists. A storage-full error must stay retryable.

## Noticed, not changed

1. The worker catches `Exception` only. An `Error` (OutOfMemoryError, UnsatisfiedLinkError) skips it; the job stays `running` until the next app start puts it back in the queue (`requeueInterrupted`).
2. A permanently failed video still shows a Retry button; pressing it fails at once again.
3. `link` and `split` are the only permanent cases today; the "video is not in the database" errors in the stages are also permanent in principle but cannot happen while a job row cascades with its video.
