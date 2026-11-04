# Eykon — recording plan v2: finish objects, start actions

Written 17 October 2026. Builds on `recording-plan.md` (14 October), which is
still the script for every object set. Cards: EYKO-50 to EYKO-53, plus EYKO-47 and EYKO-25 re-pointed.

## Where we stand

- Of the 14 October plan, only **S1-01 and S1-02** were recorded. Every
  object number so far (own50: 87 things, D-FINE + YOLOE 55 found, 15
  false on the Pixel) rests on those two clips.
- The app already labels an action on every kept frame: MobileCLIP picks
  the best of 8 prompts (`scene_prompts.json`: picking something up,
  putting something down, typing on a laptop, cooking, walking, talking to
  someone, reading, eating) if its score is 0.30 or more. **How often it is
  right has never been measured.**

## Public data first for actions, our own clips for objects

| Need | Public data enough? | Why |
|---|---|---|
| Actions (eating, typing, cooking, walking, running …) | **Mostly yes** | Everyday actions are well covered by research datasets. They save us recording and labelling time. |
| Our own things (Keys A, Earbuds …) | **No** | No dataset has *our* keys. The public sets (COCO, Objects365) are what the detectors already learned from. |
| "Where is it now", across days | **No** | Needs the same object in our places at two times. |
| Final test nobody tuned on | **No** | The panel will ask for our phone, our rooms. Keep sealed own clips. |

Action datasets to check (access and licence must be confirmed before use;
research or academic use only):

| Dataset | View | Fits because |
|---|---|---|
| Charades / Charades-Ego | Third-person / first-person pairs | Daily indoor activities, filmed in homes, with start and end times |
| Toyota Smarthome | Third-person, home cameras | Daily living: cook, drink, eat, read, use a laptop, walk |
| EPIC-KITCHENS-100 | First-person | Already used for keyframes; cooking only |
| Ego4D | First-person | Very large; needs a signed licence and approval takes time |
| Kinetics / UCF101 / HMDB51 | Third-person, web video | Many classes (running, eating, typing), but not phone-like footage |

**View: first-person** (user, 17 October 2026). The phone is held at chest
height like glasses, the same as the object clips. So first-person data
leads: Charades-Ego (its first-person half), EPIC-KITCHENS-100 (cooking,
washing dishes) and Ego4D if the licence arrives in time. The third-person
sets are only a fallback for a class the first-person sets lack.

**Risk this view brings:** the wearer's own body is mostly out of frame.
Eating, drinking, typing, cooking, reading and writing show the hands, so a
single frame can work. Walking, running and climbing stairs show only the
scene moving past. One frame may not reveal them, and they may need
motion between frames (EYKO-25). EYKO-52 must report these classes
separately.

## Action list (first draft, confirm before recording)

Eating, drinking, typing on a laptop, using a phone, cooking, washing
dishes, walking, running, climbing stairs, reading, writing, talking to
someone, picking something up, putting something down. Adding "running",
"drinking", "using a phone", "washing dishes", "climbing stairs" and
"writing" means new prompts in `scene_prompts.json` (laptop first).

## What to record (one campus session, about 2 hours)

1. **Objects:** the 14 October plan's Sets 1 (S1-03 to S1-10), 2, 6 and 7,
   unchanged. These are what EYKO-47 (tuning) and the detection close-out
   need.
2. **Actions, new Set 8** (replaces Set 5). One action per clip, 20 to 25 s:
   3 s still, about 15 s of the action, 3 s still. Each action twice, by
   two different people, **filmed by the person doing it** (phone at chest
   height, first-person). Mark one take of
   every action 🔒 sealed. Log the start and end second of the action.
3. **Mixed clips, new Set 9** (3 clips, 2 to 3 minutes each): a real
   sequence, for example walk in → sit → type → drink → stand → walk out.
   The logger writes every action change in mm:ss. This is the closest to
   real use and tests the seconds, not just the label.

Same phone settings, consent rules, log sheet and copying steps as the 14
October plan. Add a column `actions_mm_ss` to the log sheet
(`action start-end`, for example `typing 0:03-0:18`).

## Order of the work (cards)

| Card | What | Waits for |
|---|---|---|
| EYKO-50 | Record and log the clips above | the user |
| EYKO-47 | Tune detector cut-offs on the new clips | EYKO-50 |
| EYKO-51 | Close the object detection phase: score on new and sealed clips, write the finish report | EYKO-47 |
| EYKO-52 | Actions on public data: pick the dataset, score today's MobileCLIP prompts on the laptop | nothing (can start now) |
| EYKO-53 | Actions on our own clips, sealed test, laptop then Pixel | EYKO-50, EYKO-52 |
| EYKO-25 | Option B, a clip action model, only if EYKO-53 shows the per-frame prompts miss | EYKO-53 |

## What this still will not prove

Staged actions are cleaner than real life, and one campus is one
setting. The public data is the outside check, and the sealed clips are
the honest final number.
