# Vectors outside Java memory: float32, float16, int8, mapped file (EYKO-109)

Run by Zara Tahir on her Infinix X670 only, 7 November 2026. Answers supervisor questions B4 (memory) and B7,
gap G20 (vectors in memory hit the 268 MB limit). **One phone out of the two the card asks for: the A32
and the Pixel were not run.** The card's pass marks need both phones and say the lead confirms them before the run;
that confirmation was not obtained, so the verdicts below use the card's marks as written, on one phone.

## What was built (code in this branch, commit 5d26724)

`VideoVectors` can now hold a table in five ways, chosen by one constant (`VideoVectors.mode`, default `HEAP_F32`
= today's behaviour, so the app is unchanged). The database format is untouched (float32 BLOBs).

| Mode | What it holds | Bytes per 512-number vector |
|---|---|---|
| `HEAP_F32` (V0) | one Java `FloatArray`, as today | 2,048 on the Java heap |
| `DIRECT_F32` (V1) | float32 in `ByteBuffer.allocateDirect`, in chunks of 32,768 rows | 2,048 |
| `DIRECT_F16` (V2) | float16 halves in direct buffers | 1,024 |
| `DIRECT_I8` (V3) | `round(v x 127)` bytes, integer dot product, then the best 100 re-scored with the exact float32 read back from SQLite | 512 |
| `MAPPED_F32` (V4) | float32 in a file next to the database, mapped with `FileChannel.map` | 2,048, held by the OS |

Test: `OffHeapVectorTest` (`memoryAllTables`, `speedAndAnswers`), run on the phone with `am instrument`.
Vectors are the project's real own-clip vectors plus noise (`real_own_clips_90+noise`), as in EYKO-100.
Build: kit commit was not used; the test APK was built from this working tree on the laptop (the `commit`
column in the CSV says `eyko109-wip`; the code is the committed 5d26724). **The kit app on the phone was
uninstalled** to install this build (a different signing key), and the six models were pushed again.

## Finding 1: on this phone a "direct" buffer is not outside the Java heap

`DIRECT_F32` used exactly the same Java heap as the plain array (116 MB at 20,000 rows) and ran out of memory at
the same size. On this Android 13 build, `allocateDirect` memory is charged to the 268 MB Java heap limit.
The memory-mapped file (`MAPPED_F32`) is the only float32 variant that left the heap alone (3 to 5 MB).

## Memory: three tables (image 512, text 384, audio-sized 512) with the same n rows each

Java heap after loading (MB) / total PSS after (MB) / tables loaded of 3. Total PSS before loading was 55 to 58 MB.

| Rows each | `HEAP_F32` (today) | `DIRECT_F32` | `DIRECT_F16` | `DIRECT_I8` | `MAPPED_F32` |
|---|---|---|---|---|---|
| 5,000 | 31 / 85 / 3 | 31 / 85 / 3 | 17 / 72 / 3 | 10 / 65 / 3 | 3 / 85 / 3 |
| 20,000 | 116 / 166 / 3 | 116 / 166 / 3 | 59 / 113 / 3 | 31 / 86 / 3 | 3 / 166 / 3 |
| 50,000 | 183 / 230 / **2** | 183 / 230 / **2** | 145 / 191 / 3 | 74 / 124 / 3 | 4 / 325 / 3 |
| 100,000 | 208 / 251 / **1** | 208 / 251 / **1** | 183 / 231 / **2** | 146 / 195 / 3 | 5 / 598 / 3 |

Bold = `OutOfMemoryError` while loading the next table (the error text is in the CSV note). Native heap was
8 to 9 MB in every row (the mapped file does not count there; it is in PSS).
**New "rows that fit" for three tables on the Infinix:** today's way and `DIRECT_F32` fit 20,000 (50,000 fails);
`DIRECT_F16` fits 50,000 (100,000 fails); `DIRECT_I8` fits 100,000 (200,000 fails); `MAPPED_F32` fits 300,000 (the largest tested).
`MAPPED_F32` at 100,000 held 598 MB of PSS: the vectors are still in RAM when touched, only as reclaimable file
pages, not Java heap. What Android does with them under memory pressure is in the Step 6 section below.

## Speed: image table only, `VideoVectors.scores` (scores every row), median ms of 5 runs x 20 queries

| Rows | `HEAP_F32` | `DIRECT_F32` | `DIRECT_F16` | `DIRECT_I8` | `MAPPED_F32` |
|---|---|---|---|---|---|
| 5,000 | 15.8 | 17.9 | 121.9 | 30.4 | 17.7 |
| 20,000 | 60.3 | 70.0 | 480.9 | 85.2 | 67.6 |
| 50,000 | 148.9 | 170.1 | 1,197.0 | 198.1 | 167.6 |
| 100,000 | 296.8 | 339.6 | 2,340.7 | 386.4 | 341.0 |

- float32 variants are **14 to 15 % slower** than the heap array at 100,000 (339.6 and 341.0 against 296.8).
- `DIRECT_F16` is 8 times slower (the half-to-float conversion is done per number in software).
- `DIRECT_I8` is 30 % slower at 100,000 and over 200 ms there (198 ms at 50,000, just under).
- First search (loads the table), 100,000 rows: heap 20.4 s, direct 20.1 s, mapped 20.8 s, int8 28.1 s, float16 29.9 s.

## Same answers (against `HEAP_F32`, 20 queries x top 20)

| Mode | Scores bit-identical | recall@20 (5k / 20k / 50k / 100k) |
|---|---|---|
| `DIRECT_F32` | 20 of 20 queries at every size | 1.0000 at every size |
| `MAPPED_F32` | 20 of 20 queries at every size | 1.0000 at every size |
| `DIRECT_F16` | 0 of 20 (expected) | 1.0000 / 0.9975 / 1.0000 / 0.9900 |
| `DIRECT_I8` | 0 of 20 (expected) | 1.0000 / 1.0000 / 1.0000 / 0.9950 |

Not run: the whole-app check with `VideoSearchSpeedTest` (the 2,400 hits). It has a `mode` argument now, but with
float16 and int8 already failing other marks below, it would not change a verdict; it is still needed if either is considered later.

## Bigger tables: 200,000 and 300,000 rows (only the two modes that fit 100,000)

| Rows each | `DIRECT_I8` (Java heap / PSS / tables) | `MAPPED_F32` (Java heap / PSS / tables) |
|---|---|---|
| 200,000 | 185 / 236 / **2** (out of memory on the audio table) | 7 / 1,132 / 3 |
| 300,000 | 159 / 210 / **1** (out of memory on the text table) | 10 / 1,484 / 3 |

`MAPPED_F32` loads all three tables at 300,000 rows with a 10 MB Java heap, but it then holds 1.5 GB of PSS on an
8 GB phone (first load takes minutes). On a 6 GB phone such as the A32 this was **not tested**, and I would not
assume it fits: it is file-backed memory the OS may drop, not free memory.

## Whole-app search with each mode (`VideoSearchSpeedTest`, `mode` argument, 1 run, 20 queries x 20 hits per size)

Hits are (frame, window start, window end) per query, compared with `HEAP_F32`:

| Mode | Hits identical, 5k + 20k (800 hits) | Same hits in any order | Whole-app search median, 5k / 20k (ms) |
|---|---|---|---|
| `HEAP_F32` | (reference) | (reference) | 70.3 / 185.1 |
| `MAPPED_F32` | 800 of 800 | 800 of 800 | 70.4 / 192.6 (+4 % at 20k) |
| `DIRECT_I8` | 779 of 800 (97.4 %) | 779 of 800 | 80.8 / 207.7 |
| `DIRECT_F16` | 737 of 800 (92.1 %) | 799 of 800 (99.9 %) | 173.1 / 613.6 |

The card's 2,400 hits came from the larger sizes of EYKO-102; this check used 5k and 20k only (800 hits), because the app
database at 50k and 100k kept frames is much slower to build on the phone. So it is **not** the full 2,400-hit check.
Against the card's 99 % mark: `MAPPED_F32` passes; `DIRECT_I8` fails (97.4 %); `DIRECT_F16` passes only if order does not matter.

## Step 6: does Android take the memory back? (one phone, background test)

`holdInBackground`: three tables of 100,000 rows loaded with `MAPPED_F32`, held 5 minutes (23:28 to 23:38) while Chrome, the camera,
YouTube Music, Settings and the calculator were opened in turn from the laptop (three rounds), then searched again.
- The process **was not killed**: same pid (22330) for the whole time.
- PSS fell from 598 MB to 567 to 569 MB when the other apps opened: Android took back about 30 MB of the mapped pages.
- First search afterwards: image table 1,318 ms against 350 ms on repeat (3.8 times slower, pages re-read from storage);
  text 265 against 209 ms; audio 353 against 339 ms.
- Limits: this ran inside an instrumentation process, which Android protects more than a normal app, so "not killed"
  is weaker evidence than the card intends; the card asks for this on the **A32** (6 GB), which was not run. Only `MAPPED_F32` was held.

## Against the card's pass marks (one phone only)

- **V1 (float32 off-heap): not adopted.** Scores are bit-identical, but `DIRECT_F32` fails the 50k three-table mark
  (out of memory on 2 of 3 tables) and both float32 variants are 14 to 15 % slower at 100,000 (mark: within 10 %).
  `MAPPED_F32` passes the memory mark (100,000 loaded, even 300,000) and the same-hits mark, and fails the speed mark by about 5
  points at 100,000 (the whole app search is +4 % at 20,000).
- **V2 (float16): not adopted.** recall passes (0.99 at 100,000), but three tables at 100,000 do not fit, and it is 2.3 s at 100,000.
- **V3 (int8 + re-score): not adopted.** Fits three tables at 100,000 (146 MB heap) and recall is 0.995, but 386 ms at 100,000
  on the Infinix is above the 200 ms mark, the A32 is slower, and the same-hits check gives 97.4 % (mark 99 %).
- **Verdict (one phone): no variant passes all marks.** The nearest is the memory-mapped float32 file: exact answers,
  Java heap near zero, three tables up to 300,000 rows, 14 to 15 % slower than today at 100,000, survived 5 minutes in the
  background but had some pages reclaimed (first search 3.8 times slower). Whether that cost and the RAM use are acceptable is the lead's call.

## What went wrong or is not proven

- **One phone.** A32 and Pixel not run; the card's pass marks cannot be fully applied, and step 6 was not done on the A32.
- **A process crash.** Running all five modes in one process crashed it at 100,000 rows, after the heap had run out of memory twice
  (memory test, 21:00; speed test, 21:37). The cause was not found (the logcat was cleared between runs). Each remaining mode was then
  run alone at 100,000 and finished, so the 100,000 rows in the tables come from separate processes, not one run.
- **Raw logcat is partial.** The logcat buffer was cleared before each batch; the saved files are the last runs
  (`proof/infinix-2026-11-07-offheap-logcat-*.txt`). The CSVs hold every number above; they are the evidence.
- **Not done:** the 2,400-hit check at the larger sizes (800 hits at 5k and 20k only), the Head 2 document graphs (a new figure was not
  drawn), and the lead's confirmation of the pass marks. The phone was plugged in during these runs (not a thermal test). Android killed
  several unrelated background processes during the 100,000 runs (`signal 9` lines in logcat); I did not identify them and do not claim our test caused it.

## Evidence files

`docs/results/vectors/offheap/infinix-2026-11-07-eyko109-memory-*.csv` (4 files; the first is the run that crashed at 100,000)
and `...-eyko109-speed-*.csv` (6 files; 2137 crashed after the float16 rows, 2157 and 2200 are the int8 and mapped runs at 100,000),
plus the 200,000/300,000 memory files (2238 mapped, 2255 int8) and `offheap/app-search/` (whole-app hits and timings per mode),
pulled unedited from the phone. Step 6 numbers are in `proof/infinix-2026-11-07-offheap-logcat-hits-big-hold.txt`. Code: `android/.../video/VectorBlock.kt`, `VideoVectors.kt`, `OffHeapVectorTest.kt`.
