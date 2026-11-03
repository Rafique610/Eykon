# Eykon phone kit

Everything a teammate needs to run Eykon and its tests on their own phone with **only `adb`**:
no Android Studio, no Gradle, no Java. Card: EYKO-99.

The kit itself (about 1.2 GB) is **not in git**. It is shared as a folder; this README is the
copy kept in the repository. The folder holds:

| Path | What |
|---|---|
| `apk/app-debug.apk` | The Eykon app |
| `apk/app-debug-androidTest.apk` | The test app (runs the benchmarks) |
| `models/*.onnx` | The six video-pipeline models: `yolox_tiny`, `dfine_s_obj365`, `mobileclip_s2_image`, `mobileclip_s2_text`, `bge_small_en_v1.5`, `yoloe_11l_own` |
| `clips/PXL_*.mp4` | Two of our own clips (about 187 MB each) |
| `push-models.bat` / `push-models.sh` | Copies the models into the app's folder on the phone |
| `SHA256SUMS.txt` | Checksums of every file above |
| `KIT-VERSION.txt` | The commit the APKs were built from |

**Not in the kit, on purpose:** Ego4D clips (the licence forbids sharing them; use them only under
your own Ego4D licence) and the sealed held-out clips (never used for tuning).

## 0 · One-time setup on your laptop

1. Install Android **platform-tools** (it contains `adb`) and put its folder on your PATH.
2. On the phone: Settings → About phone → tap *Build number* 7 times → Developer options →
   turn on **USB debugging**. Connect by cable and accept the "Allow USB debugging?" prompt.
3. Check: `adb devices` lists your phone as `device` (not `unauthorized`).
4. Check the kit is complete: in the kit folder, `sha256sum -c SHA256SUMS.txt` (Git Bash) must say
   OK for every file.

If `adb devices` lists more than one device, add `-s <serial>` after `adb` in every command below.

**Git Bash users:** run `export MSYS_NO_PATHCONV=1` first, or Git Bash rewrites phone paths such as
`/data` and `/sdcard` into Windows paths and the commands fail. PowerShell does not need this.

## 1 · Write down your phone (device sheet)

```
adb shell getprop ro.product.manufacturer
adb shell getprop ro.product.model
adb shell getprop ro.soc.model
adb shell getprop ro.build.version.release
adb shell cat /proc/meminfo
adb shell df -h /data
```

The app needs Android 12 or newer.

## 2 · Install

```
adb install -r apk/app-debug.apk
adb install -r apk/app-debug-androidTest.apk
```

**Never** run `gradlew connectedDebugAndroidTest`: it uninstalls the app and deletes every saved
memory and model on the phone.

Open the Eykon app once (so Android creates its folder), then close it.

## 3 · Models (only for the video pipeline, EYKO-84 / EYKO-96)

From inside the kit folder:

- PowerShell: `.\push-models.bat` (the `.\` is needed)
- Command Prompt: `push-models.bat`
- Git Bash / Mac / Linux: `./push-models.sh`

It ends by listing the six files on the phone (about 690 MB; about 40 s over USB on the A32).

## 4 · Add a clip (EYKO-84 / EYKO-96)

```
adb push clips/PXL_20261014_094359202.mp4 /sdcard/Movies/
adb shell content call --uri content://media/ --method scan_volume --arg external_primary
```

The second line makes Android index the file so the app's photo picker shows it. If the clip
still does not appear, restart the phone. Then in the app: Video tab → add video → pick it.
Keep the app in front while it processes.

## 5 · Run the vector storage test (EYKO-94)

```
adb logcat -c
adb shell am instrument -w -e class com.eykon.memory.spike.VectorStorageSpikeTest com.eykon.memory.test/androidx.test.runner.AndroidJUnitRunner
adb logcat -d -s EYKO31 > <device>-<date>-logcat.txt
```

The log file is the raw evidence: do not edit it. The first lines show the device, the
SQLite version and the sqlite-vec error.

## 6 · Logs and measurements

| What | Command |
|---|---|
| Pipeline log | `adb logcat -d -s EykonVideo > pipeline-<date>.txt` |
| Battery and temperature | `adb shell dumpsys battery` (temperature is in tenths of °C) |
| App memory (PSS) | `adb shell dumpsys meminfo com.eykon.memory` (the `TOTAL PSS` line) |
| Force-stop the app (crash test) | `adb shell am force-stop com.eykon.memory` |
| Screen recording on the phone | `adb shell screenrecord /sdcard/rec.mp4` (Ctrl+C to stop), then `adb pull /sdcard/rec.mp4` |
| Screenshot | `adb exec-out screencap -p > shot.png` |

## When something fails

Copy the **exact** error text into a comment on your card, with the command you ran. A failure on
a weaker phone is a result, not a mistake.
