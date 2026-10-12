# EYKO-31 — Vector storage spike: sqlite-vec or plain BLOBs

Run 12 October 2026. Card: EYKO-31 on the Synverk board.

## Question

Can the phone use the same vector tables as the laptop? The first plan
(EYKO-1) stored vectors in sqlite-vec, a loadable SQLite extension.

## Decision

**Plain SQLite tables with vectors as float32 BLOBs, on both laptop and
phone. Each vector table is loaded into memory once and searched by dot
product. sqlite-vec is not used.** Confirmed by the user on 12 October 2026.

The rule was fixed on the card before the run: if sqlite-vec fails to load
on a phone, use BLOBs, provided a query takes under 200 ms at 20,000 vectors
on the slow phone. It failed to load, and the in-memory search took 81 ms.

## Setup

512-dimension unit vectors (random, fixed seed), 20 queries, top 20 results.
Times are per query, in milliseconds, median / worst.

| | Laptop | Phone |
|---|---|---|
| Device | development laptop, 12 CPU threads | Samsung A32 (SM-A325F), Helio G80, 6 GB RAM |
| Software | Python 3.10.6, SQLite 3.37.2, numpy 2.2.6, sqlite-vec 0.1.9 | Android 13, platform SQLite 3.32.2 |
| State | not recorded | 54 % battery, 33.6 °C, on USB |
| How to repeat | `task spike-laptop-vectors` | `task spike-android-vectors` |

The A32 stands in for the Infinix Note 12 (the project's low-end phone),
which was not available. The Pixel 9 Pro XL was not run.

## sqlite-vec on the phone

Tried on the platform SQLite that the app's Room 2.6.1 uses. Exact errors:

- `CREATE VIRTUAL TABLE ... USING vec0` → `no such module: vec0 (code 1 SQLITE_ERROR[1])`
- `SELECT load_extension('vec0')` → `no such function: load_extension (code 1 SQLITE_ERROR[1])`

Not attempted: the androidx bundled SQLite driver with a native sqlite-vec
library built per chip type. That route needs a Room upgrade and a native
build, and no official sqlite-vec Android package was found.

## Timings

| Method | Laptop 5,000 | Laptop 20,000 | Phone 5,000 | Phone 20,000 |
|---|---|---|---|---|
| BLOB, read from SQLite on every query | 24.13 / 33.64 | 91.78 / 103.32 | 245.76 / 524.97 | 1379.29 / 1459.98 |
| BLOB, vectors already in memory | 0.23 / 0.48 | 1.49 / 1.74 | 15.62 / 49.59 | 81.02 / 127.01 |
| sqlite-vec | 8.38 / 9.56 | 30.95 / 34.95 | does not load | does not load |

Other measurements:

| | 5,000 vectors | 20,000 vectors |
|---|---|---|
| Database file, BLOB | 20.5 MB (laptop), 20.6 MB (phone) | 82.1 MB (laptop), 82.2 MB (phone) |
| Database file, sqlite-vec (laptop) | 10.6 MB | 42.5 MB |
| Phone: insert all rows | 1326 ms | 3711 ms |
| Phone: Java heap in use after the run | 45 MB | 112 MB |
| Phone: native heap | 10 MB | 10 MB |

Laptop peak memory for the whole script: 254 MB.

## What follows from it

- Reading every vector from SQLite on each query is too slow on the phone
  (1.4 s at 20,000). The vectors must be loaded once and kept in memory.
- In memory, the phone is about 50 times slower than the laptop on this
  step (81 ms against 1.5 ms at 20,000), and still inside the limit.
- BLOB files are about twice the size of sqlite-vec files.
- Memory is the cost to watch: 112 MB of Java heap for one table of 20,000
  vectors, and the design has three tables (image, text, audio).

## How these numbers could be lying

- One run on one phone. Not repeated, so there is no spread.
- A cool, idle phone on a desk is the best case.
- The phone search is plain Kotlin loops over a `FloatArray`; the laptop
  uses numpy. The "50 times" gap is partly the code, not only the chip.
- Nothing above 20,000 vectors was measured.
- The low-end phone here has 6 GB of RAM; a 4 GB phone was not tested.
- The heap figure includes the test's own copies of the vectors, so it
  overstates what the search alone needs.

## Raw phone output (logcat tag `EYKO31`)

```
device samsung SM-A325F, Android 13, platform sqlite 3.32.2
option 1: CREATE VIRTUAL TABLE ... USING vec0 failed: no such module: vec0 (code 1 SQLITE_ERROR[1])
option 1: load_extension('vec0') failed: no such function: load_extension (code 1 SQLITE_ERROR[1]): , while compiling: SELECT load_extension('vec0')
n=5000 insert all: 1326 ms, file 20.6 MB
n=5000 BLOB read from SQLite + dot: median 245.76 ms, worst 524.97 ms
n=5000 BLOB already in memory, dot only: median 15.62 ms, worst 49.59 ms
n=5000 memory: java heap used 45 MB, native heap 10 MB
n=20000 insert all: 3711 ms, file 82.2 MB
n=20000 BLOB read from SQLite + dot: median 1379.29 ms, worst 1459.98 ms
n=20000 BLOB already in memory, dot only: median 81.02 ms, worst 127.01 ms
n=20000 memory: java heap used 112 MB, native heap 10 MB
```

## Raw laptop output

```
python 3.10.6  sqlite 3.37.2  numpy 2.2.6  cpu threads 12
n=  5000  BLOB read+dot: median   24.13 ms  worst   33.64 ms
n=  5000  BLOB in-memory dot: median    0.23 ms  worst    0.48 ms
n=  5000  sqlite-vec v0.1.9: median    8.38 ms  worst    9.56 ms
          file sizes: blob 20.5 MB, vec 10.6 MB
n= 20000  BLOB read+dot: median   91.78 ms  worst  103.32 ms
n= 20000  BLOB in-memory dot: median    1.49 ms  worst    1.74 ms
n= 20000  sqlite-vec v0.1.9: median   30.95 ms  worst   34.95 ms
          file sizes: blob 82.1 MB, vec 42.5 MB
peak RSS 254 MB
```

## Files

- Laptop script: `src/benchmarks/vector_storage_spike.py`
- Phone test: `android/app/src/androidTest/java/com/eykon/memory/spike/VectorStorageSpikeTest.kt`
