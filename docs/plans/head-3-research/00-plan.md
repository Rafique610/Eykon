# Head 3 review: plan (draft, 10 November 2026)

Head 3 is video intake: picker → copy → metadata → one job → ten stages → ready
(`docs/documents/source/heads/head3.json`). It is built and in use; what is missing is
**evidence**. This plan follows the Head 2 method: supervisor questions first, then the gaps
behind them, then optimisation, one card at a time. The Synverk cards are the plan; where this
file and a card disagree, the card wins.

## What is already known

| Fact | Source |
|---|---|
| Every stage logs its own time to logcat (tag `EykonVideo`) | `android/.../video/*.kt` |
| Infinix, two 75 s kit clips: 135 s and 257 s of stage time; `latest` 42 s and **136 s**, `small_objects` 31–45 s, split (frames + audio) about 36 s | `docs/results/2026-11-05-second-phone-first-run.md` |
| Pixel, old build: about 1.4 min per minute of video; 21.2 instead of about 11 min when another app was in front | `docs/results/2026-10-20-ego4d-baseline.md` |
| Video copies: about 141 MiB per minute of phone video | Infinix run above |
| No WorkManager, no file hash in the app | code search, 10 Nov |
| Kill mid-stage on a real phone: being tested now | EYKO-116 Part 3 (Zara) |

Ego4D cannot be shared and Taha's access ended 1 Nov, so every phone run uses the **kit clips**.

## Supervisor questions (Part C of the Head 3 doc)

| # | Question | Status (17 Nov, matches `head3-defense.js`) | Closes with |
|---|---|---|---|
| A1 | App killed mid-stage on a real phone? | Answered | EYKO-116 Part 3, EYKO-119 |
| A2 | App closed or another app in front? | Answered | EYKO-44, EYKO-85 (A32: EYKO-168) |
| A3 | Same video added twice? | Answered | EYKO-71 |
| A4 | Bad inputs: HEVC, HDR, portrait, variable frame rate, no GPS/time, corrupt, > 500 MB? | Answered | EYKO-118, 123, 126, 127 |
| A5 | Where do 500 MB and the four file types come from? | Answered | EYKO-122, EYKO-126 |
| B1 | Which stage takes the time, on all three phones, same build? | Answered | EYKO-117 + EYKO-123 + A32 runs 17 Nov |
| B2 | Minutes of work per minute of video on the low-end phone? | Answered | EYKO-117 + EYKO-123 + A32 runs 17 Nov |
| B3 | Battery and heat per minute of video? | Partly (Pixel battery only) | EYKO-123 |
| B4 | Ten videos queued: time until the last is ready? | Answered | EYKO-117 + EYKO-123 |
| B5 | Copy time for a large file; what if storage is full? | Partly (full storage: JVM tests only) | EYKO-71, 117, 126 |
| C1 | A resumed stage gives the same rows as a clean run? | Answered | EYKO-119 |
| C2 | Retry wastes 3 attempts on a file that can never work? | Answered | EYKO-119, 126 |
| C3 | Back-fill of a new stage on real old videos? | Partly (saved stage set back by hand) | EYKO-117, 123 |
| D1 | Why an in-app thread and not WorkManager? | Answered (now WorkManager) | EYKO-44, EYKO-122 |
| E1 | Why is `latest` the slowest stage, and can it be faster with the same output? | Answered | EYKO-120 |
| E2 | Can the models run faster (threads, XNNPACK/NNAPI, int8) with the same captions? | Open | EYKO-121 |

## Who does what

Rules: Zara builds and runs the phone harness first (Infinix) and opens a PR; Rafique reviews it,
pulls it and runs it on the Pixel and the A32. Taha works on the laptop with what is already on his
disk (slow network). Nobody waits for anybody else, except Rafique's phone run waiting for Zara's
harness (by design) and the closing doc.

Cards created on Synverk on 10 November 2026 (EYKO-44 moved to Zara by the owner the same day, to even out the load):

| Card | What | Owner | Waits for | Download |
|---|---|---|---|---|
| EYKO-117 (H3-Z1) | Phone harness: per-stage time, copy time, battery/heat, queue of N, back-fill, as CSV | Zara | — | none |
| EYKO-118 (H3-Z2) | Bad-input file set + run (made with ffmpeg from one kit clip) | Zara | — | none |
| EYKO-44 | Background worker (WorkManager, foreground notification), tested on the Infinix | Zara | — | none |
| EYKO-71 | Hash while copying, refuse duplicates, refuse a copy that will not fit | Rafique | — | none |
| EYKO-119 (H3-R3) | Stages safe to rerun + "do not retry" errors | Rafique | — | none |
| EYKO-123 (H3-R1) | Review Zara's PRs, run the harness on Pixel + A32 | Rafique | EYKO-117 | none |
| EYKO-64 | Clean Pixel timing on the kit clips + YOLOE-11S-PF cost (rewritten for kit clips) | Rafique | — | none |
| EYKO-120 (H3-T1) | `latest` and `small_objects` profiled on the laptop; faster with identical output | Taha | — | clips already on his disk |
| EYKO-121 (H3-T2) | Model runtime options and int8, laptop first, captions must match | Taha | — | none (models on disk) |
| EYKO-122 (H3-T3) | Desk research: Android background-work rules 12–17; sources for 500 MB, file types | Taha | — | none (reading only) |
| EYKO-124 (H3-R4) | Head 3 defence doc (Part C answers, figures) | Rafique | the Head 3 cards | none |

File ownership so parallel work does not collide: EYKO-44 owns `VideoWorker.kt` and
`MemoryApp.kt`; EYKO-119 owns `VideoJobs.kt` and the stage files; EYKO-71 owns `VideoCapture.kt`
and the `content_hash` column.

Later, not part of this round: EYKO-85 (background check on Pixel + A32 after EYKO-44, Rafique),
porting EYKO-120/121 winners to the phone (each becomes its own card once the laptop numbers say it wins).
EYKO-96 was renamed "MERGED into EYKO-116 (do not build)"; the owner closes it on the board.

## Order inside each person's list

- **Zara:** finish EYKO-116 → EYKO-117 → EYKO-118 → EYKO-44.
- **Rafique:** EYKO-71 → EYKO-119 → EYKO-64 → EYKO-123 when Zara's PR lands → EYKO-124.
- **Taha:** EYKO-122 (no data needed) → EYKO-120 → EYKO-121, alongside his open Head 2 cards (EYKO-91, 97, 101, 113).

## Running list (noticed, not fixed)

1. On the Infinix, `latest` took 3.2× longer on a clip of the same length (134 vs 53 sightings). Not investigated.
2. Stage times live only in logcat; nothing is stored per job, so old runs cannot be re-read.
3. EYKO-64 rewritten on 10 Nov to use the kit clips (Ego4D cannot be shared).
4. EYKO-96 renamed "MERGED into EYKO-116"; it still sits in Backlog until the owner moves it to Done (agents cannot approve).
