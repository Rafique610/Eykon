# Keep where a video was recorded (EYKO-127), Pixel, 13 Nov 2026

**Result in one line:** videos picked through the system file picker, with the media-location permission allowed, are now stored with
their recording place (33.6562, 73.0172 for the kit clip, as in the file). With the permission refused they are still added, without a place.

## Why

EYKO-126 found that no video ever got a place: the photo picker hands the app the file with its location zeroed, refuses
`MediaStore.setRequireOriginal`, and offers no option to share the location (`docs/results/2026-11-13-read-from-gallery.md`, "GPS").

## Change

- `VideoScreen`: **Add a video** asks once for `ACCESS_MEDIA_LOCATION`, then opens the system file picker (`OpenDocument`, `video/*`)
  instead of the photo picker. Refusing the permission still opens the picker.
- `AndroidManifest.xml`: `ACCESS_MEDIA_LOCATION`.
- `VideoCapture`: if the file gives no location, map the picked link to its media-store link (`MediaStore.getMediaUri`) and read the
  original (`MediaStore.setRequireOriginal`). Any failure there means "no place" (logged), never an error.

## Pixel 9 Pro XL, Android 17

Backup first (`D:\eykon-cache\backups\eyko127-2026-11-13`), both APKs with `adb install -r`. Clips: the kit clip
`PXL_20261014_094359202.mp4` (carries `+33.6562+73.0172`) plus 16 trailing bytes, so each copy has its own hash.

| Run | Permission | Stored | Notes |
|---|---|---|---|
| `eyko127_gps.mp4` | asked; "Allow all" tapped | **lat 33.6562, lon 73.0172**, `display_name = eyko127_gps.mp4`, recorded 2026-10-14T09:45:15Z, ready (10 kept, 54 sightings) | read in place in 226 ms; `source_uri = content://com.android.providers.media.documents/document/video%3A122372`. The stored hash equals the file's own SHA-256 (`7089d0d7…`): with the permission, Android hands over the original bytes |
| `eyko127_nogps.mp4` | asked again; "Don't allow" tapped | **lat/lon empty**, real name, ready | log: `no original location for content://…video%3A122373 (RuntimeException: setDataSource failed …)`, no error shown. Hash differs from the file's (location bytes zeroed) |
| `eyko127_gps_c.mp4` | granted | app message **"Saved. Recorded 14 Oct 2026, 14:45, 75 s, at 33.6562, 73.0172."** | screenshot `eyko127-pixel-saved-with-place.png` |

What Android granted on "Allow all": `ACCESS_MEDIA_LOCATION` and `READ_MEDIA_VISUAL_USER_SELECTED` (selected media only), not access to
all photos. The dialog's wording is Android's own: "Allow Eykon Memory to access photos and videos on this device?"

JVM tests pass (`testDebugUnitTest`), the app builds.

## Side effects worth knowing

- **The picker looks different:** the system file picker (Recent files, Downloads, Drive) instead of the photo grid. Gallery videos are
  under "Videos" / the device's folders.
- **Duplicate check:** with the permission the hash is of the original bytes (it now matches a laptop-side SHA-256 of the same file);
  without it, of the bytes with the location zeroed. So the same file added once with and once without the permission is not caught as
  a duplicate, and videos added through the old photo picker (zeroed hash) will not match a new add of the same file. Rare; written down.
- **Real file names** are stored now (`display_name`), so EYKO-44's notification can show them once both are merged.

## Not tested

The Infinix and the A32; a video recorded by the phone's own camera app (the kit clip is a Pixel camera file pushed by `adb`).

## Phone restored

Database and vector files put back (same SHA-256 as the backup), the 3 test folders and the test clips removed, `ACCESS_MEDIA_LOCATION`
revoked. App opened once: no crash, 22 videos ready, no job left, integrity ok.
