# EYKO-71: duplicate videos and not enough space (Head 3, A3 and B5)

10 November 2026. Built, tested on the laptop and run on the Pixel 9 Pro XL (USB, 64 % battery, 35.5 C, 7.0 GB free).

## What changed

| Part | Change |
|---|---|
| Fingerprint | `VideoCopy.copyAndHash` copies the picked file and takes its SHA-256 in the same pass (no second read). The hash is stored in a new `videos.content_hash` column (last column) with the index `videos_content_hash`, on the phone (`VideoSchema.kt`) and the laptop (`src/video_memory/schema.py`). |
| Duplicates | After the copy, `VideoRepository.findByHash` looks for a video with the same hash. If one exists the new copy's folder is deleted and the person sees "This video is already saved (recorded YYYY-MM-DD)." No row and no job are made. |
| Old databases | `VideoSchema.create` (runs on every open) adds the column to a database made before it existed, then makes the index. The laptop's `init_db` does the same. Videos saved before this change keep a NULL hash, so they are **never reported as a duplicate** of a new add (the card says to leave them). |
| Free space | Before copying, the picker's size plus a 200 MB reserve (room for frames and the database) must fit in the app's free space, else the add is refused with the numbers. If the picker gives no size, the copy is refused only when the phone is already under the reserve, and it checks again every 8 MB while copying. A disk-full error from the file system becomes a clear message. A half-written file is deleted on any failure. |
| Size limit | A picker size above 500 MB is now refused **before** copying; a file with no reported size is still stopped at 500 MB while copying (as before). |
| Log line | `EykonVideo: copy <video_id>: <bytes> bytes in <ms> ms (hash <ms> ms)`. The hash time is the time inside the digest calls, so it shows whether the hash slows the copy. Zara's EYKO-117 harness can read copy time from this line. |
| Code | `VideoCopy.kt` (new, no Android classes), `VideoCapture.kt` (`save` split into `save` + `saveStream` so a test can hand in a stream), `VideoRepository.kt` (`contentHash`, `findByHash`; the cursor positions in `listWithJobs` moved up by one), `VideoSchema.kt`, `schema.py`. |

## Checks run on the laptop

| Check | Result |
|---|---|
| `VideoCopyTest` (new, JVM): known SHA-256 vector, same bytes same hash, other bytes other hash, over-limit leaves no file, size that does not fit, unknown size, space running out part-way, disk-full error | 7 of 7 pass |
| Whole JVM suite (`testDebugUnitTest`) | 119 of 119 pass, 0 failures |
| `tests/test_schema_parity.py` (phone and laptop table designs identical, including the new column and index) | 4 of 4 pass |
| Old laptop database (no column, one row) through `init_db` twice | column added last, row kept with NULL hash, index present |
| On-device `VideoCaptureTest` (new), Pixel 9 Pro XL, `adb install -r` + `am instrument` | 4 of 4 pass: the same clip twice gives one row, one job, the message and no leftover folder; a different clip saves with its own hash; a size over 500 MB is refused before the file is opened; an old database gets the column. The 4 test folders were gone afterwards (`run-as ls`). |

## Run through the picker on the Pixel (17:30, one 12.4 s phone clip, 26.8 MB)

| Step | What logcat (`EykonVideo`) showed |
|---|---|
| First add | `copy 9490981c...: 26832141 bytes in 208 ms (hash 22 ms)`, then `split` (38 frames, 4.9 s) and `finish ... ready`; the folder holds the video and `audio16k.wav` |
| Same file added again | `copy 71275f95...: 26832141 bytes in 107 ms (hash 17 ms)`, then no `split`, no `finish`; the folder `71275f95...` does not exist; the person saw the "already saved" message; no crash in the crash buffer |

**Does the hash slow the copy?** No. The hash took 22 ms and 17 ms inside copy times of 208 ms and 107 ms: about 8 to 16 % of the copy, for roughly 129 to 250 MB/s. For a 500 MB file that is under half a second of hashing. This is one clip on one phone with a warm cache; the 107 ms second copy was faster than the first, so the copy time includes cache effects.

## Limits

- Videos saved before this change cannot be matched as duplicates (NULL hash). A one-off back-fill would have to read every stored file.
- The same video re-encoded or trimmed has different bytes, so it is not a duplicate. Only identical files are caught.
- The app killed in the middle of a copy can still leave a folder with no database row; this change does not sweep those.
- The free-space reserve (200 MB) is a first value, not measured. The real need is about 8.8 MB per minute of video for frames before dropped ones are deleted, plus the database (`2026-10-20-ego4d-baseline.md`).
