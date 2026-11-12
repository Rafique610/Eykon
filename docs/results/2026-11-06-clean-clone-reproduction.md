# Clean-clone reproduction on a second laptop (EYKO-92)

Run by Zara Tahir, started 6 November 2026 23:51 (laptop clock), finished 7 November. Question answered:
D2 "can someone else reproduce your setup?". Every number so far came from the lead's laptop; this is the
first run on another machine, from a fresh clone, following the README.

## Machine sheet

| Item | Value |
|---|---|
| Laptop | Windows 11 Home 10.0.26200, 12 CPU threads (printed by the spike) |
| Free disk before | 49.8 GB on C: |
| Python on the machine | 3.12.10 (not used: see finding 4) |
| git | 2.51.0 |
| uv | not installed at the start; 0.13.7 after `winget install` |
| Task | not installed at the start; 3.54.0 after `winget install` |
| Clone | `git clone --branch feature/video-memory` into `C:\eykon-clean`, head `972091d`, 775 files, 129 MB |
| Account | cloned with a GitHub login already on the laptop; an anonymous clone was **not** tried |

## Every step and its result

| # | Step | Result | Time |
|---|---|---|---|
| 1 | Fresh clone of the branch | OK | 11 s (23:51:32) |
| 2 | Install uv (`winget install --id astral-sh.uv -e --scope user`) | OK | with step 3: 39 s (23:58:16) |
| 3 | Install Task (`winget install --id Task.Task -e --scope user`) | OK | see step 2 |
| 4 | `uv sync` | **OK**, exit 0, 208 s | 23:59:26 |
| 5 | `task test` (`uv run pytest -q`) | **OK: 14 passed in 64.84 s**, exit 0 | 00:03:07, 74 s with start-up |
| 6 | `task smoke` | **FAILED**: `IndexError: list index out of range`, task exit 201 | 00:04:21, 52 s |
| 7 | `task spike-laptop-vectors` | **OK**, exit 0, 25 s | 11:58:14 on 7 Nov |

**Clone to green `task test`: 12 min 49 s** (23:51:32 to 00:04:21). That includes 39 s of installing
uv and Task, 208 s of `uv sync`, 74 s of `task test` and the gaps between my steps. `task smoke` was
never green on this clone.

### Why `task smoke` fails on a clean clone

`Taskfile.yml` line 38 runs `search_memories('dentist', emb, top_k=1)` and then reads `hits[0]`. The
folder `data/` is in `.gitignore`, so a clean clone has no memories. `init_db()` creates an empty
`data/memories.db`, the search finds nothing, `hits[0]` raises `IndexError`. The README describes smoke
as a check "against the real data/memories.db", which a new person does not have. The failed run also
left an empty `data/memories.db` in the clone.

## README fixes for the lead (a list to apply)

1. **uv has no install command.** The prerequisites list uv with a link only. On Windows
   `winget install --id astral-sh.uv -e --scope user` worked. (Task's `winget install Task.Task` is
   already in the README and worked.)
2. **`task smoke` fails on a fresh clone** (above). Either say that smoke needs a `data/memories.db` that
   already holds a memory about a dentist, or make the task cope with an empty database. A new person
   should be told to run `task test` first.
3. **Python 3.10+ is listed as a prerequisite but is not needed.** `.python-version` says `3.10`, and uv
   downloaded its own Python 3.10 (`.venv/pyvenv.cfg` points into `AppData\Roaming\uv\python`). The
   machine's own Python 3.12.10 was never used. Say "uv installs the right Python for you".
4. **First `task smoke` talks to Hugging Face.** It printed an unauthenticated-request warning and
   "Loading weights: 199/199", so it needs internet for the embedding model. The README does not say so.
5. **Windows symlink warning.** `huggingface_hub` warns that symlinks need Developer Mode or an
   administrator. It is harmless but looks alarming; one line in the README would help.
6. The README's own status text is out of date (the lead's gap register G15 already says so). I did not
   follow the Android sections.

## Spike comparison: `task spike-laptop-vectors` against the lead's 12 Oct laptop

Reference: `docs/results/2026-10-12-eyko-31-vector-storage.md`, "Raw laptop output". Times are median ms.
Both runs: sqlite-vec 0.1.9, numpy 2.2.6, 12 CPU threads. The lead's laptop had SQLite 3.37.2 and Python
3.10.6; this one had SQLite 3.53.1 and Python 3.10.22.

| Method | 5,000: lead | 5,000: this laptop | 20,000: lead | 20,000: this laptop |
|---|---|---|---|---|
| BLOB, read from SQLite on every query | 24.13 | 49.67 | 91.78 | 161.04 |
| BLOB, vectors already in memory | 0.23 | 0.54 | 1.49 | 3.75 |
| sqlite-vec v0.1.9 | 8.38 | 13.12 | 30.95 | 50.49 |
| Database file, BLOB (MB) | 20.5 | 20.5 | 82.1 | 82.1 |
| Database file, sqlite-vec (MB) | 10.6 | 10.6 | 42.5 | 42.5 |

- **The order of the methods matches**: in memory is fastest, sqlite-vec next, BLOB read from SQLite
  slowest, at both sizes, as the card expected.
- **This laptop is slower**: about 1.6 to 2.1 times on sqlite-vec and BLOB-read, and 2.4 to 2.5 times
  on the in-memory loop. File sizes are identical.
- Peak RSS on this laptop: 255 MB (the lead's output does not print it).
- Different laptop and different SQLite version, so only the order, not the times, is a test.

## Not tested

- An anonymous clone (no GitHub login), `task test-e2e`, `task pull-model`, `task run` and the Android
  build. The card asks only for the steps above.
- The result of step 4 is the last 25 lines of `uv sync`; the full output was not kept.

## Raw output (pasted, not summarised)

Saved with `cmd /c "task ... > file 2>&1"`, carriage returns removed. Timestamps are the laptop clock.

### uv sync (last 25 lines, with versions and timing)

```
uv: uv 0.13.7 (316c827e0 2026-11-03 x86_64-pc-windows-msvc)
task: 3.54.0
uv sync started: 2026-11-06 23:59:26
 + safetensors==0.8.0
 + scikit-learn==1.7.2
 + scipy==1.15.3
 + sentence-transformers==6.0.1
 + setuptools==84.0.0
 + shellingham==1.5.4
 + six==1.17.0
 + starlette==1.6.0
 + streamlit==1.63.0
 + sympy==1.14.0
 + threadpoolctl==3.6.0
 + tokenizers==0.23.2
 + toml==0.10.2
 + tomli==2.5.0
 + torch==2.14.0
 + tqdm==4.70.0
 + transformers==5.16.1
 + typer==0.27.2
 + typing-extensions==4.16.0
 + typing-inspection==0.4.4
 + tzdata==2026.3
 + urllib3==2.7.0
 + uvicorn==0.52.4
 + watchdog==6.0.0
 + websockets==16.1.1
uv sync exit code: 0
elapsed: 208 s

[exited with code 0]
```

### task test

```
task: [test] uv run pytest -q
..............                                                           [100%]
14 passed in 64.84s (0:01:04)
```

### task smoke (fails)

```
task: [smoke] uv run python -c "from src.config import Settings; from src.memories import init_db, count_memories, Embedder, create_memories_from_text, save_memories, search_memories; init_db(); emb = Embedder(); hits = search_memories('dentist', emb, top_k=1); print('All OK | Total in DB:', count_memories(), '| Top Hit:', hits[0][0].text, '| Fused:', round(hits[0][1], 4), '| Match:', hits[0].matc
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
C:\eykon-clean\.venv\lib\site-packages\huggingface_hub\file_download.py:142: UserWarning: `huggingface_hub` cache-system uses symlinks by default to efficiently store duplicated files but your machine does not support them in C:\Users\Zara Tahir\.cache\huggingface\hub\models--BAAI--bge-small-en-v1.5. Caching files will still work but in a degraded version that might require more space on your disk
To support symlinks on Windows, you either need to activate Developer Mode or to run Python as an administrator. In order to activate developer mode, see this article: https://docs.microsoft.com/en-us/windows/apps/get-started/enable-your-device-for-development
  warnings.warn(message)
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]Loading weights: 100%|██████████| 199/199 [00:00<00:00, 9949.54it/s]
Traceback (most recent call last):
  File "<string>", line 1, in <module>
IndexError: list index out of range
task: Failed to run task "smoke": exit status 1
```

### task spike-laptop-vectors

```
task: [spike-laptop-vectors] uv run --with sqlite-vec python src/benchmarks/vector_storage_spike.py
Installed 1 package in 18ms
python 3.10.22  sqlite 3.53.1  numpy 2.2.6  cpu threads 12
n=  5000  BLOB read+dot: median   49.67 ms  worst   58.34 ms
n=  5000  BLOB in-memory dot: median    0.54 ms  worst    1.24 ms
n=  5000  sqlite-vec v0.1.9: median   13.12 ms  worst   19.36 ms
          file sizes: blob 20.5 MB, vec 10.6 MB
n= 20000  BLOB read+dot: median  161.04 ms  worst  224.48 ms
n= 20000  BLOB in-memory dot: median    3.75 ms  worst    5.38 ms
n= 20000  sqlite-vec v0.1.9: median   50.49 ms  worst   70.25 ms
          file sizes: blob 82.1 MB, vec 42.5 MB
peak RSS 255 MB
```

