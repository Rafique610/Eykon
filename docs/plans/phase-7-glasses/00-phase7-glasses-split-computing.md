# Phase 7 — Smart Glasses and Split Computing

> Source: `docs/plans/00-roadmap.md` §2 (research problem **P4**: where to cut
> the pipeline between glasses and phone under link bandwidth and glasses
> battery) and §6; `docs/new/eykon-roadmap-v2.md` §4 (Phase 7: stretch, "can
> be kept as an analysis or simulation if time is short"). Tier: **stretch**,
> second in the cut order. Written 07 October 2026.

## Goal

Decide, with measurements, **where to split** the Eykon pipeline between a
head-worn capture device (glasses) and the phone:

| Split | Glasses does | Sent over the link | Phone does |
|---|---|---|---|
| S0 | capture only | raw / compressed video + audio | everything |
| S1 | capture + Tier 0 gates (pixel change, blur, IMU) | gated keyframes (JPEG) + VAD audio segments | Tier 1 onward |
| S2 | + Tier 1 encoder (and hand gate) | embeddings + small crops of novel frames | extraction, memory |
| S3 | + cheap extraction (path C) | slot records only (+ occasional thumbnails) | memory, answers, refinement |

For each split: link bandwidth needed, end-to-end latency (event to
queryable), energy on the glasses side and the phone side, and effect on
accuracy (what is lost when less is sent).

## Why this phase exists

- The project's long-term capture device is glasses (roadmap §1). The split
  question is a real systems trade-off: more work on glasses costs glasses
  battery; less work means more bandwidth and radio energy.
- Even without real glasses, the question can be answered with measured
  component costs (from earlier parity gates) and measured link costs between
  two phones, which keeps this stretch phase cheap and honest.

## Route options (decided in Step 01)

- **R1 — real glasses hardware** with a programmable camera (if available and
  affordable).
- **R2 — phone-as-glasses**: a second phone worn on the head runs the glasses
  side; the main phone runs the rest (planning default if no hardware).
- **R3 — analysis only**: a cost model built from measured component costs
  and measured link costs, with no live end-to-end run.

## Steps

| # | Step | Type | Key output | Depends on |
|---|---|---|---|---|
| 01 | Kickoff: route decision (R1 / R2 / R3) and scope | Decision | Route, hardware list, time box | Phase 6 Step 15 |
| 02 | Split points and data sizes per split | Analysis | Bytes per minute per split from real logs | 01, Phase 4 decision logs |
| 03 | Link characterisation: BLE and Wi-Fi Direct | Experiment (two phones) | Throughput, latency, energy per MB | 01 |
| 04 | Glasses emulation rig (phone-as-glasses) | Implement | Head-worn phone running glasses-side stages | 01, 03 |
| 05 | Transport prototype with backpressure and loss handling | Implement | Link protocol, reconnect, buffering | 03, 04 |
| 06 | Split-level experiments S0–S3 | Experiment | Bandwidth, latency, energy, accuracy per split | 02, 05 |
| 07 | Head-mount data effects on the cascade and perception | Experiment | Chest vs head results | 04, Phase 4, 4.1 |
| 08 | Cost model and projection to real glasses parameters | Analysis | Model validated on R2 data, projected with verified specs | 03, 06 |
| 09 | Recommendation and thesis chapter | Writing | Chosen split with trade-offs | 06–08 |

## Exit criteria

- Data sizes per split measured from real pipeline logs.
- Link costs measured on our phones (not taken from data sheets).
- At least two splits run end to end (R1 or R2), or the cost model validated
  against measured component costs (R3).
- A recommendation with trade-offs and stated limits (phone-as-glasses is not
  real glasses).

## Risks (pessimistic)

| Risk | Likelihood | Mitigation |
|---|---|---|
| No glasses hardware | High | R2 / R3 routes planned from the start |
| BLE throughput too low for anything but S3 | Medium | That is itself a finding; measured |
| Wi-Fi Direct unstable between the two phones | Medium | Local hotspot fallback; failures logged |
| Phone-as-glasses misrepresents glasses power | High | Cost model separates compute, camera and radio; projections labelled |
| Time runs out | High | Stretch; Step 09 can be written from Steps 02, 03 and 08 alone |

## Open decisions

- **Route** (R1 / R2 / R3) — Step 01.
- **Which link to prioritise** (BLE, Wi-Fi Direct, both) — Step 03.
