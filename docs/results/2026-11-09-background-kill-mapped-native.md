# Background kill with the adopted vector setup, `MAPPED_NATIVE` (EYKO-116 part 1)

**DRAFT: nothing here has been run yet.** Filled in by Zara Tahir on her Infinix X670 when the check is run. Checks ADR 0001 revisit
trigger 2 ("the app is killed in the background because of the mapped pages"). The pass mark is the ADR's: the process is **not killed**
(same pid at the end, and the search after the hold completes). A slower first search is reported, not failed. If it is killed, that is
the result and ADR 0001 is reopened.

## Setup

| Item | Value |
|---|---|
| Phone | Infinix X670 (A32 only if it is handed over; otherwise this is the Infinix alone, said plainly) |
| Android, RAM, free storage, battery, temperature | _from `device-sheet.txt`_ |
| Build | `feature/video-memory` at `43d610e`, both APKs installed with `adb install -r` (APK fingerprints: app `8b52e85f...`, test `5ccfe6a7...`) |
| Test | `OffHeapVectorTest#holdInBackground -e mode MAPPED_NATIVE -e n 100k -e seconds 300`, 3 tables of 100,000 rows each |
| Job queue before the test | _empty? (checked by `scripts/eyko116_bgkill.py`)_ |
| Other apps opened during the 5 minutes | _at least 5; list them_ |
| Plugged in / flight mode | _fill in_ |

Run with `python -I scripts/eyko116_bgkill.py --commit 43d610e --out docs/results/vectors/bgkill/infinix-<date>`. Never run
`connectedDebugAndroidTest` (it uninstalls the app).

## Result

| Item | Before the hold | After the hold |
|---|---|---|
| Process id (pid) | _ | _ |
| Total PSS (`dumpsys meminfo`) | _ MB | _ MB |
| Java heap | _ MB | _ MB |
| First search per table (image / text / audio) | _ / _ / _ ms | _ / _ / _ ms |
| Repeat search per table | _ / _ / _ ms | _ / _ / _ ms |

**Verdict (one line):** _killed / not killed; first search N times slower_.

## Not tested / limits

- _A32 not run (or: run on the A32 on <date>)._
- _Which apps were open and how much memory they took is not controlled._

## Evidence files

`docs/results/vectors/bgkill/infinix-<date>/`: `device-sheet.txt`, `meminfo-before.txt`, `meminfo-after.txt`,
`eyko109-logcat.txt` (raw `logcat -d -s EYKO109`), `instrument-output.txt`; a logcat screenshot is on the EYKO-116 card.
