# Step 02 — Mobile Emulation Profile + Parity Harness

## What
Infrastructure so every laptop experiment runs under phone-like constraints
and every result can be compared with the phone later:
1. A **mobile emulation profile** (CPU-only, pinned threads, RAM ceiling).
2. **Wall-clock replay**: a video is fed frame-by-frame at real speed (e.g.
   3 fps), not as fast as possible; frames that arrive while the pipeline is
   busy are counted as *dropped* or *queued*.
3. **Run recorder**: every run writes `data/runs/<run_id>/` with config,
   decisions log, per-stage latency, RSS samples, CPU %, dropped frames.
4. **Golden fixtures**: `data/golden/` — small set of frames/IMU windows/audio
   chunks + expected outputs (gate decisions, embeddings rounded) as JSON,
   readable by Python tests and Kotlin unit tests.

## Why
The Phase 3 soak test ran batch-style; it can't show live backlog. And without
shared fixtures there is no way to prove the Kotlin port makes the same
decisions as the Python research code — the exact "worked on laptop, broke on
phone" trap you want to avoid.

## How to implement
- Settings in `src/config.py` (`MEMORY_` prefix): `emu_profile`
  (`flagship`/`lowend`/`off`), `emu_threads`, `emu_ram_mb`, `replay_fps`.
- `src/vision/replay.py`: generator yielding `(t_wall, t_video, frame)` at
  `replay_fps` using `time.monotonic()`; consumer signals busy/free.
- RAM watchdog thread with `psutil` (already a dependency): sample every
  500 ms, mark run `failed_ram` above ceiling.
- `cpu_affinity` to first N cores; `n_threads=N` for llama.cpp / LiteRT.
- `src/benchmarks/run_recorder.py`: append-only JSONL writer (stdlib `json`).
- Golden fixtures: pick 50 frames from ego_v1 covering static / motion / blur /
  dark / scene change; store PNG + `expected.json`.

## Open decisions
- **Low-end RAM ceiling**: (a) 2.0 GB — Infinix has 8 GB but Android + apps
  leave ~2–3 GB for us; (b) 1.5 GB — safer for 4–6 GB phones; (c) measure on
  Infinix first (Step 03) and set from data.
- **Fixture format for images**: (a) PNG — lossless, identical on both sides;
  (b) raw YUV_420_888 — exactly what CameraX gives, but harder to view;
  (c) both for a subset — catches colour-conversion bugs.

## You test this
- Run one Phase 3 video through wall-clock replay with the current captioner
  and look at the run summary: how many frames dropped/queued? (Expect a lot —
  that's the point.) Tell me if the summary is readable enough for you.

## How this number could be lying
- Laptop cores at 4 threads are still much faster than phone cores — only the
  phone parity gate gives the real slowdown factor; the profile limits
  resources, it does not emulate ARM.
- `psutil` RSS misses mmap'd model pages that Android counts → record both RSS
  and USS/PSS where available.

## Verification
- [ ] Same video, same config → same decision log (deterministic).
- [ ] Run marked failed when RAM ceiling exceeded (test with tiny ceiling).
- [ ] Replay at 3 fps for 60 s video delivers 180 ± 2 frames.
- [ ] `task test` still passes.

## Files changed
- [NEW] `src/vision/replay.py`, `src/benchmarks/run_recorder.py`, `data/golden/`
- [MODIFY] `src/config.py`, `Taskfile.yml`, `README.md`

## Dependencies
- Step 01 (frames for golden fixtures; can start with Phase 3 videos).

## Common issues
- Windows `cpu_affinity` works; thread count must also be set in the model
  runtime, otherwise it ignores affinity.
- `time.sleep` jitter on Windows ~15 ms — fine at 2–4 fps.
