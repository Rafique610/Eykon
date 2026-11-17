# Accepted video types: avi out, 3gp / mkv / webm in (Pixel, 17 Nov 2026)

Head 3 question A5 (where do the file types come from?). EYKO-122 (`docs/research/2026-11-16-head3-background-and-limits.md`, Part 2)
recommended accepting the types Android lists for decoding and dropping `.avi`, which failed on the Infinix and the Pixel (EYKO-118 B10c).
**Phones:** Pixel only (rule "Which phone a card runs on"): the type list is the same code on every phone, and Android's own media
index decides the MIME type; the A32 would not change the answer.

## Change
- Phone `VideoMetadata.TYPES`: mp4, mov, m4v, **3gp** (`video/3gpp`, `video/3gpp2`), **mkv** (`video/x-matroska`), **webm** (`video/webm`);
  `video/x-msvideo` and `video/avi` removed. The refusal message lists the six (`TYPE_NAMES`).
- Laptop `src/config.py` `video_types`: the same six (laptop and phone stay in step).
- Tests: `VideoMetadataTest.onlyTheSixLaptopTypesAreAccepted` (avi refused); JVM 123 of 123; laptop pytest 44 of 44.

## Check on the Pixel 9 Pro XL (Android 17)
Build from the working tree on top of 531b3a4, `adb install -r` (never `connectedDebugAndroidTest`). App data backed up whole first
(`D:\eykon-cache\backups\pixel-types-2026-11-17`). Four 15 s files cut from kit clip 1 with ffmpeg (imageio-ffmpeg), added through the
app's Video tab and the system file picker, driven over adb.

| File | MIME type Android gave it | Result | Kept frames |
|---|---|---|---|
| T1 H.264 + AAC, `.3gp` (480p) | `video/mp4` | read in place, **ready** | 2 of 45 |
| T2 VP9 + Opus, `.webm` (720p) | `video/webm` | read in place, **ready** | 3 of 45 |
| T3 H.264 + AAC, `.mkv` | `video/x-matroska` | read in place, **ready** | 3 of 45 |
| T4 MPEG-4 + MP3, `.avi` (EYKO-118 B10c) | `video/avi` | **refused**: "This file type is not supported. Use one of: mp4, mov, m4v, 3gp, mkv, webm." | — |

Log lines: `head3/pixel-2026-11-17-file-types-eykonvideo.txt`. Screenshot of the refusal: `head3/pixel-2026-11-17-avi-refused.png`.

## Reading
- webm and mkv now work end to end; before, both were refused at the picker check (EYKO-118 B11 for mkv).
- `.avi` is refused at once with a clear message, instead of being accepted and then failing as "damaged" (EYKO-118 bug 2).
- **Our `.3gp` file was given `video/mp4` by Android's media index**, so it went in through the mp4 entry, not the new `video/3gpp` one.
  Phone-recorded 3gp (H.263 / AMR) was not tried; whether it is indexed as `video/3gpp` is not known.

## Clean-up
Only the three folders this test created (their ids from the `read` lines) were deleted; the database and vector files were put back from
the backup (same SHA-256), the 22 video folders match the backup, and the four test files were removed from Movies.

## Limits
One phone, ffmpeg-made files, 15 s each. No real 3gp or webm from another app (screen recorders, web downloads).
