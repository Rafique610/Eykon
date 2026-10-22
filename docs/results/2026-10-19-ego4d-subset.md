# Ego4D episodic-memory subset (EYKO-54)

19 October 2026. The outside test for search, latest sighting and actions.
Data lives on `D:/eykon-cache/ego4d/` only: never in git (licence: academic
use, no redistribution). Access is valid until 1 November 2026 (us-west-1).

## What was downloaded

| Part | Command | Size |
|---|---|---|
| EM annotations v2_1 (NLQ, VQ, moments: train, val, test without answers) | `ego4d --datasets annotations --benchmarks EM` | 0.1404 GB (9 files) |
| 24 validation clips | `ego4d --datasets clips --video_uid_file selection/clip_uids.txt` | 1.5376 GB (CLI estimate); 1.6 G on disk |

Run through `uv run --with ego4d python -m ego4d.cli.cli -o D:/eykon-cache/ego4d ...`.
The CLI prints the size and waits for y/n, so nothing downloads unseen.

## The validation split

| Task | Clips | Source videos | Typical clip |
|---|---|---|---|
| NLQ (typed question → time window) | 415 | 300 | 480 s |
| VQ (photo of an object → last time seen) | 1159 | 414 | 300 s |
| MQ (action → start and end) | 528 | 329 | 480 s |

No clip appears in all three tasks, but 80 source videos do.

MQ labels that match our action list (count of labels in val):
converse 643, use_phone 393, read 144, stir while cooking 83, stairs 65,
wash dishes 64, drink 59, stir before cooking 48, cut food 41,
use laptop 21, eat a snack 20, write notes 5.

## How the 24 clips were chosen

1. From the 80 shared videos, the 8 MQ clips with the most of our action labels.
2. From the same 7 source videos, the 8 NLQ clips with the most questions and the 8 VQ clips with the most valid queries.

| Task | Clips | Minutes | Queries or labels |
|---|---|---|---|
| MQ | 8 | 64 | 100 |
| NLQ | 8 | 73 | 90 |
| VQ | 8 | 40 | 39 |
| **Total** | **24** | **177** | |

The list and the picking script are in `D:/eykon-cache/ego4d/selection/`
(`clip_uids.txt`, `video_uids.txt`, `ego_pick2.py`).

## Checked after download

Read with OpenCV on the laptop:
- 24 files, matching the list exactly. None unreadable.
- 177.0 minutes in total.
- All at 30 fps: 18 clips at 1440x1080, 4 at 1920x1080, 2 at 1280x720.
- 1.6 G on D:.

## Limits

- 7 source videos means few people and places. This is a first outside
  check, not a full benchmark score.
- Walking and running are not MQ classes (only stairs). Eating and
  writing are rare (20 and 5 labels in the whole val split).
- Ego4D is mostly head-mounted cameras; our phone is at chest height.
- These are validation clips, so official test-server numbers are not
  comparable. Report them as "Ego4D val subset".
