# Read videos from the gallery instead of copying them (EYKO-126), Pixel, 13 Nov 2026

**Result in one line:** the app no longer copies a picked video. It keeps the picker's read permission and decodes the gallery file in place.
An hour of camera video now costs about **126 MB** of app storage instead of about **9.2 GB** (EYKO-116, calculated), and the 500 MB limit is gone.
Deleting the gallery file after a video is ready does not affect search. Deleting it mid-processing fails the job at once, with a clear message.

## Setup

| Item | Value |
|---|---|
| Phone | Pixel 9 Pro XL, Android 17 (SDK 37), USB |
| Build | branch `rafique/eyko-126-read-from-gallery` (uncommitted at test time), both APKs with `adb install -r` (never `connectedDebugAndroidTest`) |
| App data before | 22 videos, all ready; backup of the database and folder list taken first, restored at the end (see "Phone restored") |
| Clips | made from the kit clip `PXL_20261014_094359202.mp4` (1080p HEVC, 20 Mbps, carries GPS `+33.6562+73.0172`) and `..._094903187.mp4`, with ffmpeg 7.1 from `imageio_ffmpeg`. Each one differs in bytes from every saved video (trailing `free` atom, a cut, or a re-encode), so none is refused as a duplicate |
| Added how | through the app's own **Add a video** button and the system photo picker (Google Photos picker), driven with `adb shell input` |

## What was checked

| # | Check | Clip | Result |
|---|---|---|---|
| 1 | Read in place, no copy | t1, 74.5 s, 186,496,596 B | Log: `read 13f7af5a…: 186496596 bytes in place in 762 ms (no copy)`. Ready in 72 s; same output as the clean run of 11 Nov (EYKO-119): 224 frames, 10 kept, 6 found, 54 sightings. The video's folder holds `audio16k.wav`, `clip_vectors.bin` and 10 frames: **3,008 KB, no `.mp4`** |
| 2 | Database row | t1 | `source_uri = content://media/picker/0/com.android.providers.media.photopicker/media/122350`, `display_name = 122350.mp4`, `recorded_at` read from the file (2026-10-14T09:45:15Z), `lat`/`lon` empty (see 7). The 22 old videos got the two new columns (NULL) without any change to their rows |
| 3 | Gallery file deleted after ready: search still works | t2, seconds 40–70 of the kit clip, 30 s | File deleted and the media index rescanned, app force-stopped and reopened, search "keys": the result **"0.0–9.5 s (best at 8.0 s), likeness 0.211"** can only come from t2 (the same frame in the older full copy of the clip is at 48.0 s). Screenshot `eyko126/pixel-search-after-source-deleted.png` |
| 4 | Gallery file deleted mid-processing | t3, 75 s | Deleted 4 s into `split`, app force-stopped 3 s later, then reopened. The job failed at once: **1 attempt** (not 3), error `PermanentFailure: the original video was deleted from the phone or can no longer be read`, video `failed`. Screenshot `eyko126/pixel-source-deleted-mid-processing.png` |
| 5 | Over 500 MB (was refused before, EYKO-118 B12) | t4, the kit clip looped 4 times with `-c copy`, 4 min 58 s, **743,552,939 B** | Accepted: `read aaf1a61c…: 743552939 bytes in place in 3566 ms (no copy)`. Ready in 2 min 53 s (894 frames, 13 kept, 6 found, 66 sightings). Folder **10,204 KB** |
| 6 | HDR-tagged and portrait (EYKO-118 B3, B4) | 15 s each: HEVC 10-bit tagged BT.2020/PQ; H.264 with a 90° display rotation | Both ready, 0 attempts. B3 kept frame has normal colour. B4 kept frames are 360×640: the app applies the rotation tag, as a player shows the file. Frames: `eyko126/B3-hdr-kept-frame-000013.jpg`, `eyko126/B4-portrait-kept-frame-000041.jpg` |
| 7 | GPS (EYKO-118 bug 1) | t1, a real camera clip with GPS | **Not stored.** See "GPS" below |
| 8 | On-device tests | — | 14 video test classes, 97 tests: 96 passed, 1 failed (`VideoCaptureTest` still expected `content_hash` as the last column; updated to check all three new columns), then `VideoCaptureTest` 4/4. Log `eyko126/pixel-ondevice-video-tests.txt` |

## Storage

| | Before (copy) | Now (in place) |
|---|---|---|
| t4, 297.8 s of 20 Mbps camera video | 743.6 MB copy + about 10 MB | **10.2 MB** (audio 9.5 MB, 13 frames, vectors) |
| Per hour of this camera video | about 9.2 GB (EYKO-116 Part 2 (b), calculated) | **about 126 MB** (10,448,896 B / 297.8 s × 3600; audio alone 115 MB) |
| All six test clips (1,202.9 MB of video) | about 1.2 GB of copies | app `files/` grew by **20,227 KB** (805,211 → 825,438 KB) |

The 16 kHz audio is now 91 % of what a video costs. Deleting it after speech has been processed is the next saving, when speech exists (EYKO-7/8).

## GPS

None of the 22 videos already on the Pixel has a location, and neither does t1, although the kit clip carries one.
So the cause is not Zara's test files: **the photo picker hides the location.** It serves the file with its `©xyz` location atom zeroed
(the app's hash of t1 differs from the file's own SHA-256; the atom is at byte 186,392,656).

Tried on the phone with a throwaway probe test (not kept): with `ACCESS_MEDIA_LOCATION` granted, `MediaStore.setRequireOriginal(uri)` on the picker
link throws `UnsupportedOperationException: Require original is only supported for Picker URIs when location sharing is explicitly granted by the user`,
and this picker (Google Photos, Android 17) offered no location option anywhere (selection bar, preview, menu). The permission was revoked and the
manifest change removed again.

**Not fixable inside this card.** Getting the location needs a different way of picking (the system file browser, `ACTION_OPEN_DOCUMENT`,
plus `ACCESS_MEDIA_LOCATION` and `setRequireOriginal`, untested) or a picker version that asks the person to share location. That changes how
people add videos, so it is a decision for the owner: a separate card.

## Side effects worth knowing

- **Duplicate check:** the hash is of the bytes the picker serves (location zeroed), not of the original file. Every add goes through the picker
  (the old copy path too), so duplicates are still found; it only means the hash cannot be compared with a laptop-side hash of the same file.
- **Display name:** the picker gives a media number (`122350.mp4`), not the file's real name. It is stored, but it is not useful to show.
  EYKO-44's notification should keep "Video n of m".
- **Retry on a gone source:** the failed card still offers Retry; it fails the same way, at once.

## Not tested

- The permission after a **reboot** with EYKO-44's background worker (step 8): EYKO-44 is not merged. To check with EYKO-85.
- The **Infinix** and the A32 (the card names the Infinix; only the Pixel was available). The copy fallback (phone refuses to keep the permission) did not happen on the Pixel, so that branch was not exercised on a phone; it is the old, tested copy path.
- A real camera clip larger than 500 MB (t4 is a camera clip looped 4 times).

## Phone restored

Backup before the test: `D:\eykon-cache\backups\eyko126-2026-11-13b` (database, vector file, folder list). After the test: the database and
vector file put back (same SHA-256 as the backup), the stale `-wal`/`-shm` of the test removed, the 6 test video folders removed (the folder list
matches the backup), the test clips removed from the gallery. Then the app was opened once: no crash, 22 videos ready, the two new columns added,
no job left. Integrity check ok.

## Evidence

`docs/results/eyko126/`: on-device test log, two screenshots, two kept frames, and `pixel-eykonvideo-log.txt` (the app's `EykonVideo` lines for
each run, copied from this session's `adb logcat` output).
