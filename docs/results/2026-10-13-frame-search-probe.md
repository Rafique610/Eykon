# Probe: can a typed phrase find the right frames? (13 October 2026)

**In one line:** searching the frames' MobileCLIP vectors with a typed phrase works very well for
things that fill the scene (sheets of paper, a table tennis table, a car) and is close to chance
for a small thing such as a phone on a desk. Neither this nor the detector finds phones reliably.

A laptop check done ahead of card EYKO-19, to learn whether vector search covers what the
detector (card EYKO-9) misses. Nothing was built into the app.

## What was run

- The same 44 kept frames as the EYKO-9 measurement (six evaluation clips, pulled from the Pixel).
- MobileCLIP-S2 image and text encoders on the laptop (`task probe-frame-search`,
  `src/benchmarks/frame_search_probe.py`). The phone's image vectors agree with the laptop's to
  cosine 0.997 or better, so the ranking should carry over; that was not re-checked here.
- Labels: `perception/presence-2026-10-13.csv`: for eight things, whether each frame visibly shows
  it. Written by the AI assistant from the pictures before any search ran. **Not yet checked by
  a person.** The scoring rules were also fixed first; they are at the top of the script.
- Detector column: YOLOX-Tiny on the Pixel (`perception/pixel9proxl-2026-10-13-tiny.json`),
  scored on these same presence labels.

## Result

"Avg precision" is 1.00 when every frame showing the thing is ranked above every frame that does
not; a random order scores about the "chance" column.

| Thing (phrase typed) | Frames showing it | Chance | Search: first five right | Search: avg precision | Detector: frames found | Detector: wrong frames listed |
|---|---|---|---|---|---|---|
| a phone | 16 | 0.36 | 3 of 5 | 0.43 | 5 of 16 | 0 |
| a laptop | 9 | 0.20 | 4 of 5 | 0.76 | 7 of 9 | 1 |
| a chair | 17 | 0.39 | 3 of 5 | 0.51 | 13 of 17 | 10 |
| a backpack | 6 | 0.14 | 2 of 5 | 0.58 | 0 of 6 | 0 |
| a car | 1 | 0.02 | 1 of 1 | 1.00 | 1 of 1 | 0 |
| a computer monitor | 7 | 0.16 | 3 of 5 | 0.52 | 5 of 7 | 0 |
| sheets of paper | 28 | 0.64 | 5 of 5 | 0.97 | no such class | |
| a table tennis table | 4 | 0.09 | 4 of 4 | 1.00 | no such class | |

Putting "a photo of" in front of the phrase changed avg precision by at most 0.05 either way.

## What it shows

- **Search covers things the detector has no name for.** Paper and the table tennis table were
  ranked almost perfectly. This is the open-vocabulary benefit, and it is real.
- **Search is weak for small things.** "A phone" scored 0.43 against a chance of 0.36. A whole
  frame's vector describes the scene; a phone covering a few percent of the picture barely
  moves it.
- **The detector is precise but misses a lot.** When Tiny says "cell phone" it was right every
  time, but it said so in only 5 of the 16 frames that show one. It found no backpack at all.
- **The two fail differently.** The detector is better on laptops, monitors and chairs; search is
  better on backpacks and on anything outside the 80 classes. Used together they cover more than
  either alone, which is what the rank fusion card (EYKO-23) is for.
- **One frame attracts everything.** `clip4_000065` (a bag on a cluttered desk) came first for
  phone, laptop, chair, backpack and monitor. It was right for two of the five.

## What it means for "where are my keys?"

Keys are smaller than a phone and are not a detector class. On this evidence neither whole-frame
search nor the detector would find them. That leaves the hand-centred crop matching of card
EYKO-32 (look closely at the small region where the hands are) and, if that is also weak, the
small vision-language model on the kept frames (Option C). This probe is the measured reason
those two cards matter.

## Limits

- 44 frames from six short clips. Frames from one clip look alike, so part of each score is
  "found the right clip", not "found the thing".
- One marker (an AI), no second check; "visible and recognisable" is a judgement for small or
  partly hidden things.
- Laptop vectors, not the phone's own. No timing was measured.
- The same clips were used for the keyframe and detector work, so this is not unseen data.
