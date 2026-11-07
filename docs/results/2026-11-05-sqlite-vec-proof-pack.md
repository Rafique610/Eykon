# Proof pack: sqlite-vec does not load on any of our three phones (EYKO-94)

5 November 2026. Supervisor questions answered: A1 "did you actually run it? show me the error" and
A4 "only on one phone?". Every row below links to a raw log; nothing is summarised from memory.

## The claim

The app cannot use the `sqlite-vec` extension (`vec0`) on a phone, because Android's own SQLite
does not let an app load an extension. The same two errors appear on all three phones.

## Three phones, same test

Test: `VectorStorageSpikeTest` from the phone kit, run with
`adb shell am instrument -w -e class com.eykon.memory.spike.VectorStorageSpikeTest com.eykon.memory.test/androidx.test.runner.AndroidJUnitRunner`.

| | Samsung Galaxy A32 | Pixel 9 Pro XL | Infinix X670 |
|---|---|---|---|
| Run by | the lead's agent | the lead's agent | Zara Tahir |
| Date | 3 Nov 2026 | 3 Nov 2026 | 5 Nov 2026 |
| Android | 13 | 17 | 13 |
| Platform SQLite | 3.32.2 | 3.50.6 | 3.32.2 |
| Device sheet | [a32](vectors/proof/a32-2026-11-03-device.txt) | [pixel](vectors/proof/pixel9proxl-2026-11-03-device.txt) | [infinix](vectors/proof/infinix-2026-11-05-device.txt) |
| Raw log | [a32](vectors/proof/a32-2026-11-03-logcat.txt) | [pixel](vectors/proof/pixel9proxl-2026-11-03-logcat.txt) | [run 1](vectors/proof/infinix-2026-11-05-logcat.txt), [run 2 after restart](vectors/proof/infinix-2026-11-05-logcat-run2.txt) |
| Error 1 | `CREATE VIRTUAL TABLE ... USING vec0 failed: no such module: vec0` | same | same |
| Error 2 | `load_extension('vec0') failed: no such function: load_extension` | same | same |
| Recording | none | none | see "Recording" below |

Exact lines, copied from the raw logs:

```
a32:     I EYKO31 : option 1: CREATE VIRTUAL TABLE ... USING vec0 failed: no such module: vec0 (code 1 SQLITE_ERROR[1])
a32:     I EYKO31 : option 1: load_extension('vec0') failed: no such function: load_extension (code 1 SQLITE_ERROR[1]): , while compiling: SELECT load_extension('vec0')
pixel:   I EYKO31 : option 1: CREATE VIRTUAL TABLE ... USING vec0 failed: no such module: vec0 (code 1 SQLITE_ERROR)
pixel:   I EYKO31 : option 1: load_extension('vec0') failed: no such function: load_extension (code 1 SQLITE_ERROR): , while compiling: SELECT load_extension('vec0')
infinix: I EYKO31 : option 1: CREATE VIRTUAL TABLE ... USING vec0 failed: no such module: vec0 (code 1 SQLITE_ERROR)
infinix: I EYKO31 : option 1: load_extension('vec0') failed: no such function: load_extension (code 1 SQLITE_ERROR): , while compiling: SELECT load_extension('vec0')
```

A newer SQLite does not help: the Pixel has 3.50.6 and fails the same way as the two phones with 3.32.2.

## Infinix again after a restart (not a one-off)

Run 1 (14:14 to 14:20) was recorded. The phone had been up 1 week 1 day. The phone was then restarted
(uptime 9 minutes at 14:38, so it booted about 14:29) and the same script ran again, starting 14:30:04
(not recorded; the card asks only for the restart and the rerun).

| | Run 1 | Run 2, after restart |
|---|---|---|
| `no such module: vec0` | yes | yes |
| `no such function: load_extension` | yes | yes |
| `fts5` / `rtree` missing | yes / yes | yes / yes |
| Platform SQLite | 3.32.2 | 3.32.2 |
| All-three-tables memory test | 3 of 3 at 5k and 20k, 2 of 3 at 50k, 1 of 3 at 100k | the same |
| Terminal summary | not kept | `Time: 320.792`, `OK (3 tests)` |
| Raw log | 60 lines | 60 lines |

The error lines are identical apart from the process ids. The "OK (3 tests)" line is in the terminal
output, not in the raw log.

## Extra checks in the newer test (same on all three phones)

The lead's 4 Nov logs for the A32 and Pixel ([a32](vectors/proof/a32-2026-11-04-extensions-logcat.txt),
[pixel](vectors/proof/pixel9proxl-2026-11-04-extensions-logcat.txt)) and the Infinix log above show the
same results:

- Loading any extension fails, not only `vec0` (`load_extension('eyko_no_such_extension')` gives the same `no such function: load_extension`).
- Built-in modules: `fts4` works; `fts5` and `rtree` are not compiled in (`no such module`).
- Compile options list: none.

## What the Infinix run also showed (not part of the claim)

The same test run printed an all-three-tables memory check (image, text and audio vectors held in
memory together). On the Infinix (Java heap limit 268 MB):

| Rows per table | Tables loaded | Result |
|---|---|---|
| 5,000 | 3 of 3 | PSS 61 to 86 MB |
| 20,000 | 3 of 3 | PSS 86 to 167 MB |
| 50,000 | 2 of 3 | `OutOfMemoryError` loading `audio_vec` (100 MB allocation) |
| 100,000 | 1 of 3 | `OutOfMemoryError` loading `text_vec` (150 MB allocation) |

It also ran a 5k and 20k speed sweep. Those numbers (for example `blob_disk_dot` 20k median about 1.1 s,
`blob_memory_fast` 20k about 14 ms) come from an uncontrolled run: phone charging, other apps open.
They are **not** EYKO-95 results and should not be quoted as such.

## Evidence files

| File | What |
|---|---|
| `vectors/proof/infinix-2026-11-05-logcat.txt` | Raw `adb logcat -d -s EYKO31` of the recorded run (60 lines), unedited except that a Windows byte-order mark and carriage returns were removed. |
| `vectors/proof/infinix-2026-11-05-logcat-run2.txt` | Raw log of run 2, after a phone restart (60 lines, same clean-up as run 1). |
| `vectors/proof/infinix-2026-11-05-device.txt` | Device sheet, same format as the lead's. |
| Drive folder (link under "Recording") | The screen recording of run 1 and the terminal screenshot of the error lines. Not in the repo (size). |

## Recording

Screen recording of the terminal while `run-eyko94.ps1` runs the test and saves the log (155 MB,
too big for the repo; the test itself takes about 5 minutes). The same Drive folder holds the terminal
screenshot of the error lines:
<https://drive.google.com/drive/folders/1bEhHK31968-6kjmqncOu3Knt8hs9QYhB>

## Still to do

- Screenshot is attached to the card (done 7 Nov).
- The script that ran the test is committed as `docs/phone-kit/run-eyko94.ps1` (7 Nov), so others can rerun it.
- The two CSVs the test wrote on 5 Nov (`eyko100-memory-...1414.csv`, `eyko90-...1417.csv`) are still on the phone;
  to be pulled and committed as an uncontrolled run.
- Head 2 document (A1 and A4): left to the lead at merge; not edited here.

## What this does not prove

- It shows the error on three phones. It does not show it on every Android version.
- The Infinix log lacks the final `OK (n tests)` line (it appears in the recording, not in the log).
- One earlier rehearsal and one earlier attempt the same afternoon were not kept.
