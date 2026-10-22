# Phase 6 Step 04 — Asymmetric Scheduler (Research Problem P3)

## What

A scheduler that shares one phone chip between continuous perception and
occasional user questions (plus background jobs), with explicit priorities:

| Priority | Work | Rule |
|---|---|---|
| 1 (highest) | user question being answered | starts immediately; may pause lower work |
| 2 | cheap perception (Tier 0 / Tier 1 / path C) | must keep up with capture at the current rate |
| 3 | speech (VAD + ASR) on speech segments | bounded delay (e.g. transcript within N minutes) |
| 4 | VLM refinement (path V queue) | only when 1–3 are idle and thermal state allows |
| 5 (lowest) | consolidation, conversation summaries | while charging or idle (Phase 5, 5.1) |

Mechanisms:

- **Preemption**: when a question arrives, VLM refinement in progress is
  paused or cancelled (re-queued); perception rate may be reduced for the
  question's duration.
- **Rate control**: the perception frame rate adapts to keep queue ages
  bounded.
- **Budgets**: maximum heavy-model calls per hour (roadmap KPI: target 120,
  minimum acceptable 300).

Experiment: compare (a) no scheduler (first-come, first-served), (b) static
priorities, (c) priorities + preemption + rate control, on a fixed live
workload (replayed session with scripted questions every few minutes).

## Why

- Research problem P3 (roadmap §2): perception and live Q&A compete for the
  same chip, memory bus and thermal budget. Without a scheduler, a question
  can wait behind a VLM call (Phase 3 measured about 13 s per frame on a
  laptop), or perception backs up while answering.
- The comparison with "no scheduler" is the evidence that the scheduling
  design matters.

## How to implement

1. `Scheduler` (Kotlin) with priority queues and a small number of worker
   coroutines; stages submit jobs with priority and an estimated cost (from
   measured averages).
2. Preemption: long jobs (VLM, generative) check a cancellation flag between
   steps (between frames / tokens where the runtime allows).
3. Rate control loop every few seconds: if queue age above a limit, lower
   frame rate one step; if below, raise it.
4. Laptop simulation (`src/benchmarks/scheduler_sim.py`) with measured stage
   costs from the parity gates, to explore policies quickly before phone runs.
5. Phone experiment on both phones: question latency P50 / P90 / worst,
   perception backlog, dropped frames, heavy calls per hour, energy, for
   policies (a), (b), (c).

## Open decisions

- **Preemption style.** Options: (a) cancel and re-queue — simple, wastes
  partial work; (b) pause and resume — keeps work, needs runtime support;
  (c) let short jobs finish, cancel long ones (draft).
- **Perception during questions.** Options: (a) keep full rate; (b) reduce
  rate during answering (draft); (c) pause perception completely for the
  answer duration.

## You test this

1. During a live 15-minute run, ask a question every 2 minutes with each
   policy. Which policy felt fastest?
2. Look at the backlog plot for each policy.

## How this number could be lying

- A simulation with average costs hides variance; phone runs are the result,
  simulation only guides choices.
- Scripted question timing is regular; real questions come in bursts; one run
  with a burst of 5 quick questions is included.

## Verification

- [ ] Scheduler implemented with priorities, preemption and rate control.
- [ ] Laptop simulation reproduces phone trends roughly (checked).
- [ ] Policy comparison on both phones with question latency, backlog, drops,
      calls per hour and energy.
- [ ] Chosen policy recorded with reasons.

## Files changed

- [NEW] `android/.../live/Scheduler.kt`
- [NEW] `src/benchmarks/scheduler_sim.py`
- [NEW] `docs/results/phase-6/step04-scheduler.md`
- [MODIFY] `android/.../live/LivePipeline.kt`, `README.md`

## Dependencies

- Step 03.

## Common issues

- Coroutines on a shared dispatcher ignore priorities; use separate
  dispatchers or an explicit queue with a fixed worker count.
