# Phase 6.5 Step 05 — Grouping Faces and User Naming

## What

1. **Grouping**: cluster good-quality face descriptors within the retention
   window (online threshold clustering, as for places in Phase 4.1 Step 08).
2. **Naming screen**: the user sees a group (2–4 small crops shown only on
   the device), and can: name it (only after the in-app consent record for
   that person is ticked), mark "don't remember this person" (descriptors
   deleted), merge or split groups.
3. **Named people**: a `people` table (id, name, consent_recorded_at,
   created_at); named groups keep their descriptors beyond the retention
   window; unnamed groups expire.
4. **Confirmations**: when a new face matches a named person with medium
   confidence, the app can ask "Is this Alex?" (optional, off by default);
   answers improve the group.

## Why

- Only user-confirmed names (principle from Step 01): the system never names
  anyone by itself.
- Merge / split and "don't remember" give the user control and give us a
  measure of how much correction grouping needs.

## How to implement

1. `src/people/groups.py` and Kotlin mirror.
2. Naming screen in the app; consent checkbox required before saving a name;
   consent time stored.
3. Evaluation on consented sessions: group purity, over-splitting, number of
   user actions needed to reach correct groups.

## Open decisions

- **Show face crops at all.** Options: (a) small crops on the naming screen
  only, deleted after naming (draft); (b) no crops — name from the keyframe
  context only (harder); (c) keep one thumbnail per named person.
- **"Is this Alex?" prompts.** Options: (a) off (draft); (b) on with a daily
  limit; (c) only in a review screen, never as notifications.

## You test this

1. After a session with two consenting friends, name both groups. How many
   merges or splits were needed?
2. Mark one group "don't remember" and confirm its data is gone.

## How this number could be lying

- Few people and few sessions make grouping easy; results state participant
  and session counts.

## Verification

- [ ] Grouping, naming (consent-gated), merge, split, "don't remember" work on
      the phone.
- [ ] Purity, over-splitting and user actions measured on consented data.
- [ ] Unnamed groups expire as designed.

## Files changed

- [NEW] `src/people/groups.py`, `android/.../people/NamePeopleScreen.kt`
- [MODIFY] database schema (`people`), `README.md`

## Dependencies

- Step 04.

## Common issues

- The same person in different lighting splits into two groups; merging must
  be easy.
