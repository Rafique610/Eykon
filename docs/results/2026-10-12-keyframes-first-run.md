# Keyframe comparison — first run, before any tuning

Run 12 October 2026. Card EYKO-45. Rules: `docs/plans/keyframe-comparison-protocol.md`.

> **AI-marked, not yet checked by a person.** The 35 key moments were marked by an AI
> assistant from still frames, not by Rafique from the video (protocol section 8).
> Every number below carries that limit until a person has checked at least two clips.

## Short version

**As built today, with untuned thresholds, our method does not beat the phone baselines.**
It keeps more than half of all frames, so at that budget every method finds almost every
moment and the test cannot tell them apart; and on the phone ours costs about ten times
more than uniform sampling, almost all of it in the image model.

## What was run

- **Clips:** six, 138 s in total, about 480 x 640, shared through WhatsApp (re-compressed).
  Tuning clips 1, 2, 4, 5 (26 moments); held-out clips 3, 6 (9 moments).
- **Ours:** the app's own code on a Pixel 9 Pro XL (Android 17, debug build): frames at 3 per
  second, cheap filters, hash, MobileCLIP-S2. Thresholds are the cards' starting values.
- **Budget:** every other method was set to keep as many frames per clip as ours kept,
  where it can be set.
- **Not run:** Katna (not yet wired in); the Samsung A32 (not connected); the public
  OVP / VSUMM set (its official page needs a sign-in).

## Table 1 — quality (laptop), all six clips

| Method | Frames kept | Kept per minute | Moments hit | Wasted frames |
|---|---|---|---|---|
| **Ours** (from the phone) | 227 | 98.4 | 34 of 35 | 51 of 227 (22 %) |
| B0 Uniform sampling | 227 | 98.4 | 35 of 35 | 53 of 227 (23 %) |
| B1 Codec keyframes (cannot be set to a budget) | 142 | 61.6 | 35 of 35 | 32 of 142 (23 %) |
| B2 ffmpeg scene filter | 227 | 98.4 | 33 of 35 | 73 of 227 (32 %) |
| B3 PySceneDetect, content | 138 | 59.8 | 35 of 35 | 34 of 138 (25 %) |
| B3 PySceneDetect, adaptive | 163 | 70.7 | 31 of 35 | 46 of 163 (28 %) |

PySceneDetect could not always be pushed up to the budget, so it kept fewer frames.

Split by group (moments hit):

| Method | Tuning clips (26) | Held-out clips (9) |
|---|---|---|
| Ours | 26 | 8 |
| B0 Uniform | 26 | 9 |
| B1 Codec keyframes | 26 | 9 |
| B2 ffmpeg scene filter | 26 | 7 |
| B3 PySceneDetect, content | 26 | 9 |
| B3 PySceneDetect, adaptive | 22 | 9 |

Per clip (moments hit / frames kept):

| Method | clip 1 | clip 2 | clip 3 | clip 4 | clip 5 | clip 6 |
|---|---|---|---|---|---|---|
| Ours | 11/11 with 102 | 3/3 with 11 | 4/5 with 20 | 7/7 with 55 | 5/5 with 20 | 4/4 with 19 |
| B0 Uniform | 11/11 with 102 | 3/3 with 11 | 5/5 with 20 | 7/7 with 55 | 5/5 with 20 | 4/4 with 19 |
| B1 Codec keyframes | 11/11 with 67 | 3/3 with 13 | 5/5 with 16 | 7/7 with 22 | 5/5 with 15 | 4/4 with 9 |
| B2 ffmpeg scene filter | 11/11 with 102 | 3/3 with 11 | 3/5 with 20 | 7/7 with 55 | 5/5 with 20 | 4/4 with 19 |
| B3 PySceneDetect, content | 11/11 with 66 | 3/3 with 11 | 5/5 with 20 | 7/7 with 17 | 5/5 with 14 | 4/4 with 10 |
| B3 PySceneDetect, adaptive | 9/11 with 60 | 3/3 with 11 | 5/5 with 19 | 7/7 with 54 | 3/5 with 8 | 4/4 with 11 |

## Table 2 — cost on the phone (Pixel 9 Pro XL)

Median of three runs per clip, summed over the six clips (138.4 s of video).

| Method | Work per minute of video | Where the time goes |
|---|---|---|
| **Ours** | 137.5 s | pull frames and audio 21.3 s; cheap filters 1.4 s; hash + MobileCLIP 114.7 s |
| B0 Uniform sampling (same number of frames) | 13.4 s | decoding and saving the frames |
| B1 Codec keyframes | 12.5 s | listing them 0.4 s; saving them 12.1 s |

- Ours is slower than real time (2.3 times the video's length) and about ten times the cost of either baseline.
- 83 % of ours is the last layer (the image model).
- Memory with the model loaded: about 323 MB native.
- Battery 66 % to 65 %, battery temperature 34.6 °C to 36.6 °C over the 19-minute run (which also includes the baselines). The model slowed from about 280–540 ms per frame in earlier short runs to about 700 ms during this run.

What each layer of ours dropped, of 416 frames pulled:

| Layer | Frames dropped |
|---|---|
| Dark, bright, blurry | 0 |
| Unchanged since the last kept frame | 2 |
| Hash or MobileCLIP duplicate | 187 |
| **Kept** | **227 (55 %)** |

## What this says

1. **The budget is too generous to compare anything.** At about 98 frames a minute, even evenly spaced frames land in every moment. The comparison only becomes meaningful at much smaller budgets, and the protocol's second view (recall against frames kept) is the one to use.
2. **Ours is not selective enough.** The dark, bright and blurry checks never fired on these clips, "unchanged" fired twice, and the model's 0.95 similarity bar lets most hand-held frames through.
3. **Ours is expensive for what it does today.** Because the cheap layers pass almost everything, the model runs on most frames.
4. **The one moment ours missed** (clip 3, held out) and the ones the scene-based tools missed are single cases; with 35 moments one case is 3 points.

## What follows (protocol step 5: tune, on the tuning clips only)

- Tune the blur threshold, the "unchanged" thresholds, the hash distance and the similarity bar so ours keeps far fewer frames; report recall at several budgets (for example 10, 20, 40 frames a minute) for every method.
- Reduce model calls: stricter cheap layers first; then a smaller or faster model setting.
- Then run once on the held-out clips, and on the Samsung A32.

## How these numbers could be lying

- AI-marked moments, by the same assistant that builds the method, from frames 0.5 s apart.
- Six short clips, one person's recordings, re-compressed by WhatsApp; 35 moments.
- Moments are wide (often several seconds), which favours any method that samples often.
- "Ours" quality comes from the phone run; the other methods ran on the laptop on the same files.
- One phone, debug build, phone warm by the end; the A32 was not measured.
- Uniform sampling and codec keyframes save pictures only; they do no checking at all, so their cost is a floor, not a like-for-like service.

## Files

- Marks: `docs/results/keyframes/moments-2026-10-12.csv`
- Phone results: `docs/results/keyframes/pixel9proxl-2026-10-12.json`
- Laptop scoring: `src/benchmarks/keyframe_eval.py` (`task eval-keyframes -- <phone json>`)
- Phone benchmark: `android/app/src/androidTest/java/com/eykon/memory/video/KeyframeBenchmarkTest.kt`
