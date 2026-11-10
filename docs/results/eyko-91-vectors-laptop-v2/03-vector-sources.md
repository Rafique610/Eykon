# 3 · Which vectors to test on

Every result row says which vectors it used (`source_vectors`). The plan uses **three
sources**, because they answer different questions.

| Source | `source_vectors` label | What it is | Answers | Comparable with |
|---|---|---|---|---|
| **S1 · random** | `random_unit_seed31` | Gaussian 512-d unit vectors, seed 31; queries from seed 90 (as EYKO-90) | speed and memory; worst case for an approximate index | v1, the 3 Nov phone sweep |
| **S2 · phone "real"** | `real_own_clips_90+noise` | The **same 90 own-clip vectors** the phones use (`android/app/src/androidTest/assets/vectors/own_image_512.f32`, `own_text_384.f32`). Copies after the first 90 get noise 0.01 per number (≈ 0.97 cosine); queries get noise 0.05 | speed with the same data as the phones (B3) | the 4 Nov phone sweep |
| **S3 · varied real** | e.g. `real_epic_mobileclip` | Many **different** real frames, embedded with the same MobileCLIP-S2 model as the app; queries are real **text** phrases through the MobileCLIP text encoder, as in the app | **accuracy** of float16, int8 and the approximate index (A5, B7, EYKO-109) | — (new) |

## Why S2 alone is not enough

S2 is right for **timing**. An exact dot product does the same work whatever the numbers are,
and the 4 Nov phone run showed real and random times match (Head 2, B3).

S2 is **wrong for accuracy**. At 100k, 99.9 % of the vectors are noisy copies of only 90
frames. The true top 20 for a query is then about 20 near-identical copies of one frame, which
differ only by noise. Any method that rounds the numbers (float16, int8) or skips some vectors
(HNSW) will shuffle those copies and show a low recall that means nothing. The opposite risk
also exists: a clustered set can make an approximate index look better than it is. So recall is
reported on **S1 (worst case) and S3 (realistic case)**, and only listed for S2.

The noise is drawn with numpy, not Java's `Random`, so S2 matches the phones in kind but not
bit for bit. That is fine for timing, and the write-up will say so.

## The card's step 5 and a licence problem

The card says to read `image_vec` / `text_vec` "from a copy of the Pixel database (ask the lead
for `memories.db`)". Two facts change that:

1. **The Pixel database also holds Ego4D vectors.** EYKO-56 ran 4 Ego4D clips through the app
   on the Pixel. The lead's own `src/benchmarks/export_own_vectors.py` says: *"Never point this
   at a database with Ego4D clips: the licence forbids sharing anything from them."*
2. **Ego4D access ended on 1 November 2026.** `docs/results/2026-10-19-ego4d-subset.md`: *"Access
   is valid until 1 November 2026."* Whether vectors already derived from the clips may still be
   used after that date is a licence question I cannot settle. The plan does not touch them.

**Proposal:** use only the own-clip vectors the lead already exported. They are committed (90 per
table) and are what the phones use, so laptop and phone stay on the same data. If the lead
exports more own-clip vectors (own clips only), S2 grows without any licence question.

Where the card and the docs disagree, the card wins and I say so. Here the card's wording
predates both facts, so this is flagged for the lead rather than followed blindly.

## Options for S3 (varied real vectors)

What it must have: real images like a phone user's, embedded with MobileCLIP-S2; a licence that
allows academic use; and it has to fit in **15 GB of free disk**, so it is streamed (download,
embed, delete, keep only the vectors: 100k × 2 KB = 205 MB).

| Option | Domain | Licence | Size / effort | Queries | Fit |
|---|---|---|---|---|---|
| **EPIC-KITCHENS-100**, a slice of videos, frames at 1 per 2–3 s | **first-person, everyday** (like our users; the project already used it for keyframes, Head 4) | CC BY-NC 4.0 (academic use fine) | Full set ≈ 740 GB, so **video by video** with the official script (`--specific-videos`, Python 3.5+, no libraries); per-video size not published, so measure one | real narrations ("open fridge", "pick up knife") through the text encoder | **best match** |
| COCO 2017 (train 118k + val 5k) through streaming | everyday photos, not first-person | annotations CC BY 4.0; images under Flickr terms (terms page could not be read: **verify**) | train is ≈ 18 GB, more than the free disk, so stream it | 5 human captions per image | good scale, wrong viewpoint |
| Own clips, every frame at 3 fps (not only kept frames) | exactly ours | ours | a few thousand frames; needs the lead's clips | object words from Head 5 (keys, wallet …) | most real, too small |
| Ego4D | first-person | **access ended 1 Nov** | — | — | **excluded** |

**S3 is required, not optional. The probe showed why** ([evidence](evidence/probe-results-2026-11-05.txt)).
On 20k random 512-d vectors the true top 20 have a cosine of only about 0.144, while all
scores have a std of 0.044. Random vectors have no neighbourhoods, which is the worst possible
case for a graph index:

- usearch at its default settings found **0.20–0.25** of the true top 20.
- It needs connectivity 32 and expansion_search 1024 to reach 0.997, and then takes 8.3 ms per
  query on one thread, slower than numpy brute force (4.5 ms).

So an approximate index judged on random vectors fails for reasons that say nothing about real
use. **Its pass mark has to be judged on S3.** S1 is still run and reported, labelled as the
worst case.

**How large S3 needs to be:** the card judges the index "at 300k". 300k varied real vectors means
about 170 hours of video at one frame every 2 s, far beyond this laptop's disk and a reasonable
download. **Proposal:** S3 goes as large as the time budget allows (target **100k**), and the
pass mark is judged at the largest S3 size, with the brute-force time at 300k measured on S1 and
S2 for the speed side. This changes the card's wording, so the lead confirms it before anything
runs ([05](05-pass-marks-and-risks.md)).

**Decision (Taha (lead), 6 Nov 2026):** EPIC-KITCHENS-100, a slice of about 30 videos, streamed, frames every 2 s,
MobileCLIP-S2 image vectors, with narrations as text queries, up to the largest size that fits
the time budget (target 100k). COCO is the fallback if the EPIC downloads are too slow.

**Updated (Taha (lead), 8 Nov 2026):** 30 typical videos are only about 4.2 h, so one frame every 2 s gives about 7.5k vectors, too small to judge an index (brute force is about 3 ms there). From EPIC's own `EPIC_100_video_info.csv`, the **30 longest videos** (31–62 min each, 20.8 h, 74,841 s) at **one frame every 0.75 s** give about 100k. Frames 0.75 s apart are still distinct; the 6.5 frames/s that 30 typical videos would need gives near-duplicates, S2's problem. The list of the 30: P01_109, P01_18, P01_09, P23_102, P10_04, P35_104, P30_05, P35_108, P30_107, P13_08, P27_103, P20_04, P23_04, P25_107, P33_105, P02_09, P22_07, P35_105, P01_105, P23_103, P29_03, P04_05, P07_10, P12_101, P22_109, P24_09, P12_04, P04_105, P06_101, P12_02.

**Changed again (Taha (lead), 8 Nov 2026): S3 = COCO, the fallback.** EPIC's server gave the real file sizes: the 30 longest videos are 1080p 60 fps, about 13 GB per hour, **≈ 250 GB** in all (largest 13.4 GB, more than the disk's free space), and the connection was down to 1–8 KB/s. S3 is now **COCO train2017**: the first 100k photos in image-id order (of 118,287), each fetched into memory, embedded with MobileCLIP-S2 and dropped (no image is saved; ≈ 16 GB fetched in all). Queries: the first caption of 21 **val2017** photos (seed 90), real text from photos not in the stored set, through the text encoder. Label `real_coco_train2017_mobileclip_s2`; files in `data/eyko91_coco/` (git-ignored). Model run through open_clip in PyTorch (CPU build); its ONNX export, which the phone runs, agrees to cosine ≥ 0.999. **Caveat:** COCO is everyday photos, not first-person video; it answers "does the index hold its recall on real, varied vectors at 100k", not "on our users' footage".

**Changed back (Taha (lead), 10 Nov 2026): S3 = EPIC-KITCHENS, the 30 longest videos** (the list above). The 258 GB of video is more than the free disk, so `embed_epic.py` **never saves a video**: it streams each one from EPIC's server over 24 parallel range requests (the server gives about 0.1–0.5 MB/s per connection; 24 together reached ≈ 4.5 MB/s on 10 Nov, about 1.5× real time for 1080p50 HEVC), decodes it as it arrives, takes the first decoded frame at or after every **0.745 s** (0.75 s gives 99,774 frames, 226 short of the 100k size; 0.745 s gives ≈ 100,441), and embeds them with MobileCLIP-S2 through open_clip in PyTorch (torch 2.14.1+cpu, open_clip 4.2.1, timm 1.0.31, PyAV 17.1.0). A video's rows are written once it is done, so a stopped run resumes at the next video. 258 GB is streamed in all (all 30 checked on the server, 10 Nov; largest P01_18, 13.9 GB). It runs on this laptop when the connection allows (EYKO-113); the connection swung between 0.26 and 4.7 MB/s on 10 Nov. Queries: 21 distinct narrations (seed 90) from EPIC_100_validation.csv, none from the 30 stored videos (P24_09 is in the validation set, so its narrations are left out). Label `real_epic_kitchens_30_longest_mobileclip_s2`; files in `data/eyko91_epic/` (git-ignored; EPIC-KITCHENS is CC BY-NC 4.0). The file is video after video, so each size takes a seeded random set of rows (seed 91) kept in time order: every size spans all 30 kitchens, and a smaller size's frames are always among a larger one's. The COCO embedder was removed (it is in git history, 5982255).

## What S3 needs that the laptop does not have yet

- **MobileCLIP-S2 ONNX** (image and text encoders): exported with the existing `task export-clip`
  / `task export-clip-text` (≈ 2 GB of tools and weights; research-only licence, never shipped).
  The same ONNX files as the phone, so the vectors are the app's vectors.
- **Embedding speed on this CPU** is not known. Measure it on 500 frames first and write down the
  hours it implies before starting the full run.
- PyTorch from PyPI on Linux pulls CUDA libraries (several GB) unless the CPU wheel index is used.
  With 15 GB free, the export must use the CPU build.
