# EYKO-118: what Eykon does with awkward video files (Infinix X670, 12 Nov 2026)

Phone: Infinix X670, Android 13. App build on the phone: `zara/eyko-44-workmanager` at 5a192c7 (WorkManager foreground worker; it also refuses a second copy of the same bytes). No app code was changed for this card.
Files: made by `src/benchmarks/make_bad_inputs.py` from one kit clip (10-20 s each, 14 files, git-ignored in `data/bad-inputs/`). They were pushed to `/sdcard/Movies` and added through the app's picker. The app does not store the original file name, so each accepted video was matched to its file by byte size in the `EykonVideo` log.
Screenshots of the refusals (B10c, B11, B12) are on the card; the B12 one also shows "Saved videos (9)".
Raw log lines: `docs/results/head3/bad-inputs/infinix-2026-11-12-eykonvideo.txt` (Eykon lines only).

## Result per file

| File | What it tests | At the picker / add | Message shown | Stage it failed at | Retry helps? | Recorded time | GPS | Frames kept (filter, then dedup) | Crash | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 h264 baseline .mp4 | control | accepted | none | none (ready) | n/a | 14 Oct 2026, read from the file | **none stored**, though the file has a location tag | 5 of 45, then 3 | no | OK, GPS missing (bug 1) |
| B2 HEVC 8-bit | HEVC | accepted | none | none (ready) | n/a | from the file | none stored (file has a tag) | 5, then 2 | no | OK |
| B3 HEVC 10-bit, HDR-tagged | HDR | accepted | none | none (ready) | n/a | from the file | none stored (file has a tag) | 5, then 3 | no | OK (colour of the kept frames not inspected) |
| B4 portrait, rotation 90 | rotation tag | accepted | none | none (ready) | n/a | from the file | none stored (file has a tag) | 5, then 2 | no | OK (orientation of kept frames not inspected) |
| B5 variable frame rate | VFR | accepted | none | none (ready) | n/a | from the file | none stored (file has a tag) | 4 of 45, then 2 | no | OK |
| B6 metadata stripped | no time, no GPS | accepted | none | none (ready) | n/a | **time it was added** (12 Nov 08:29 UTC), because the file has none | none (file has none) | 5, then 3 | no | OK (falls back to the add time) |
| B7 truncated (last 30% cut) | corrupt file | **refused** | "This file does not contain a video that can be read." (the same message as B10c, seen on the phone; the B10c screenshot shows it) | at add, after a full copy (copied 3 times, no leftover file) | n/a, no job is made | none | none | none | no | unclear error (bug 3) |
| B8 audio-only .mp4 | no video track | **not offered**: the photo picker does not list it (Android indexes it as audio) | none | none | n/a | none | none | none | no | not testable through the picker (bug 4) |
| B9 video, no audio | no audio track | accepted | none | none (ready) | n/a | from the file | none stored (file has a tag) | 5, then 3 | no | OK |
| B10a .mov | accepted type | accepted | none | none (ready) | n/a | from the file | none stored (file has a tag) | 5, then 3 | no | OK |
| B10b .m4v | accepted type | accepted | none | none (ready) | n/a | from the file | none stored (file has a tag) | 5, then 3 | no | OK |
| B10c .avi (MPEG-4 video + MP3) | accepted type | **refused** | "This file does not contain a video that can be read." (screenshot) | at add, after a full copy (copied twice, no leftover file) | n/a | none | none | none | no | unclear error, and `.avi` is listed as accepted (bug 2) |
| B11 .mkv | wrong type | **refused** | "This file type is not supported. Use one of: mp4, mov, m4v, avi." (screenshot) | at add, before any copy | n/a | none | none | none | no | clear error |
| B12 over 500 MB | size limit | **refused** | "This file is larger than the limit of 500 MB." (screenshot) | at add, before any copy | n/a | none | none | none | no | clear error |

B12 is 528,327,965 bytes against the 524,288,000-byte limit: about 1% over (0.8%).
The 9 accepted videos went through every stage with 0 attempts and no error text on any job. Once queued together they took about 25-40 s each. Second adds of B10a and B10b (their sizes appear twice in the log) were not stored: 9 videos exist, not 11.

## Bugs and oddities, for Rafique (nothing was fixed)

1. **GPS is never stored.** Eight of the files carry a location tag (per ffprobe at make time), including the B1 control, and the app stored none for any of them. The parser itself handles that format (the app's `VideoMetadataTest` covers it), so the value never reached it. A likely cause is that Android hides a picked file's location unless the app holds the media-location permission; **not tested, cause not established.** Real phone clips may behave the same.
2. **`.avi` is listed as accepted but fails.** B10c is an MPEG-4 video in an `.avi`. ffprobe on the laptop reads it, but Android cannot: the phone's own media index has no duration or size for it, and the gallery showed 0:00. The app then says "This file does not contain a video that can be read." Only one `.avi` was tried, so whether any `.avi` works on this phone is not known. The app still lists `avi` as a supported type.
3. **The truncated file is refused for the same reason.** B7 also showed 0:00 in the gallery, so Android cannot read it, and the app's message is true as far as it goes, but it does not say the file is damaged.
4. **The picker cannot offer an audio-only `.mp4`** (B8), so that case could not be tried. Not a bug in Eykon's check, only a limit of the system photo picker.
5. B7 and B10c are copied in full before they are refused (the app then removes the copy; no leftover files were found). A large damaged file would cost its full copy time before the error.
6. A file with no recording time (B6) shows the time it was added as its recorded time. Reasonable, but it looks like a real recording time in the app.

## Not checked

- Whether B4's portrait frames and B3's HDR frames are stored the right way up and with sensible colour (only that the stages finished).
- The refusal wording for the second add of B10a and B10b (I did not capture it).
- Build: EYKO-71 changes duplicates and free space; this run is on the build named above.
