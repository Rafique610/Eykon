# Ego4D: six changes, chosen on set A, checked on held-out set B (EYKO-57 to EYKO-63)

20–21 October 2026, laptop only. The baseline is `2026-10-20-ego4d-baseline.md`.
- **Set A:** the 24 clips of that baseline (7 videos, 177 min). Each change was chosen here by a rule fixed in its script before scoring.
- **Set B:** 24 new validation clips, picked by the same rule from 5 other videos (194 min, `task ego4d-select -- B A`), never used to choose anything. It holds fewer questions (32 object and 4 people NLQ, 35–38 VQ, 49 MQ), so its numbers move more easily.

## Results

| # | Change | Card | Script | Set A | Set B | Verdict |
|---|---|---|---|---|---|---|
| 1 | Search returns windows that grow over neighbouring frames scoring ≥ 0.85 × the hit (gap ≤ 10 s) | EYKO-58 | `ego4d_eval.py` (`windows`) | NLQ objects R@1 0.3/0.5: 10.3/6.4 → **16.7/9.0**; R@5: 20.5/10.3 → **32.1/20.5** | R@1: 12.5/6.2 → **25.0/15.6**; R@5: 28.1/15.6 → **37.5/25.0** | Keep |
| 5a | Delete dropped frames' JPEGs in the last stage | EYKO-59 | `VideoPipeline.kt` (VideoFinish) | storage only; JVM tests pass, the phone test compiles | | Keep (phone check later) |
| 2 | Action prompts: first-person wording, +6 actions, smoothing ±6 s | EYKO-60 | `ego4d_actions.py` | MQ F1 10.8 → **32.2** (found 18 → 40 %, precision 7.7 → 27 %) | F1 15.4 → **16.7** (found 28.6 → 36.7 %, precision 10.6 → 10.8 %) | Keep, small real gain; most of A's gain did not carry over |
| 3 | Hybrid search: BM25 + bge over 15 / 30 s caption windows, fused with RRF | EYKO-61 | `ego4d_hybrid.py` | worse in every mix (hit@1 24.4 → 15–21 %) | pictures + bge 15 s better (R@1 0.3: 28.1 → 34.4), keywords worse | Drop for now: our detector-list captions rarely share words with questions |
| 4 | Last seen: crops of any object (YOLOE-11S prompt-free, 10 boxes ≥ 0.10), MobileCLIP vectors, cut-off 0.87 | EYKO-62 | `ego4d_lastseen.py` | VQ success 35.9 → **46.2 %** (app crops in the same script) | 22.9 → **34.3 %** | Keep; cost 1.9–2.3 s a frame on the laptop, phone not measured |
| 5b | YOLOE only where MobileCLIP flags keys or earbuds (cosine ≥ 0.15) | EYKO-63 | `ego4d_gate.py` | YOLOE on 15.2 % of frames; own50: all 18 right finds kept | YOLOE on 19.6 % of frames; finds 8 → 2 (unlabelled) | Keep |

## Details

### 1 · Windows
Chosen on set A by the mean of the four R@k numbers over all 90 questions. The grow settings were 0.95, 0.9, 0.85 and 0.8; 0.85 won. People questions (12 on A, 4 on B) stay near zero: the search cannot tell people apart.

### 2 · Actions (set A, chosen variant)

| Class | Found | Precision of the label |
|---|---|---|
| use phone (23) | 0 → 34.8 % | 66.7 % |
| converse (8) | 25 → 50 % | 35.1 → 52.2 % |
| drink (3) | 0 → 66.7 % | 2.8 % |

Reading, eating, cutting and washing dishes stay at 0. Set B ranks the unsmoothed version higher (F1 18.2). That hints the ±6 s smoothing was fitted to set A, but B cannot be used to choose.

### 3 · Hybrid search
The captions are lists of detector names ("car and street lights, 1 person, inside a car"). Ego4D questions ask about specific things ("where did I put the fire gun?"). Captions with attributes (EYKO-26, Option C) are the condition for trying this again.

### 4 · Last seen

| Crops / vectors | A success | A seen | B success | B seen |
|---|---|---|---|---|
| app / MobileCLIP 0.87 | 35.9 | 20.5 | 22.9 | 11.4 |
| app / DINOv2-S 0.6 | 35.9 | 28.2 | 17.1 | 5.7 |
| **anything / MobileCLIP 0.87** | **46.2** | 25.6 | **34.3** | 22.9 |
| anything / DINOv2-S 0.6 | 38.5 | 30.8 | 31.4 | 22.9 |

DINOv2-S did not beat MobileCLIP for the answer, so no new vector model is needed, only the prompt-free detector. The app-crops row here is 2.6 points above the baseline report (33.3 %), because this script re-decodes frames by seeking. Changes are only compared within one script.

### 5b · YOLOE gate
Of 18 right YOLOE finds on our own clips, all are kept at C = 0.15. Those clips are full of keys and earbuds, so YOLOE still runs on 96 % of their frames. On everyday Ego4D video it runs on 15–20 % of frames. YOLOE was about half of the phone's 1.4 min per video minute, so the expected saving is large, **not yet measured on the phone**.

## What still needs a phone

- **Ported and testable:** 5a.
- **Laptop-only results:** 1, 2, 5b and 4. Porting each means changing the app's code. 2 also changes `scene_prompts.json` and the `src/config.py` action list.
- **4 adds a model:** YOLOE-11S prompt-free (AGPL, academic use) must be exported and timed on the Pixel first.

## Limits

- The question counts are small, especially on set B (32 + 4 NLQ).
- Validation clips only, scored with our own scripts.
- Set A was used to choose. Only set B numbers are unbiased.
