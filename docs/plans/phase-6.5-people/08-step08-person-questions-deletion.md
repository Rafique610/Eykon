# Phase 6.5 Step 08 — Person Questions and Deletion Flows

## What

1. **Questions**:
   - "What did Alex say about X?" → `who_said` / `conversation_recall` filtered
     by the named speaker;
   - "When did I last see Alex?" → latest keyframe with Alex's named face
     group, with time and place (template answer with evidence);
   - "What did I talk about with Alex?" → sessions where Alex spoke, topics
     and summaries.
   Router intents added; answers through the Phase 5.2 answer layer.
2. **Deletion**: "Forget Alex" removes the person row, face descriptors,
   voiceprints, links, and names from utterances (replaced by "speaker N" or
   removed per the user's choice); a test verifies nothing remains in any
   table or index.
3. **Off switch**: turning the feature off deletes all people data after a
   confirmation (or keeps it disabled, by user choice), and stops detection.

## Why

- Person questions are the user value of this phase; deletion is the privacy
  promise of Step 01 made real and testable.

## How to implement

1. Router intents and templates (rules-first).
2. Deletion function covering every people-related table and the indexes; a
   check script that searches for the person id and name everywhere.
3. UI: person page with "forget" and a list of what will be deleted.

## Open decisions

- **Past utterances after forgetting.** Options: (a) revert to "speaker N"
  (draft); (b) delete the person's utterances entirely; (c) ask.

## You test this

1. Ask the three person questions about a consented friend.
2. Forget them; ask again; confirm nothing names them anywhere.

## How this number could be lying

- Deletion tested on small data; the check script also runs on the full field
  study database.

## Verification

- [ ] Person questions answered with evidence.
- [ ] "Forget person" and the off switch remove all people data (check
      script passes).

## Files changed

- [MODIFY] `src/memories/router.py`, `src/answers/templates.py`
- [NEW] `src/people/delete.py`, `android/.../people/PersonScreen.kt`
- [MODIFY] `README.md`

## Dependencies

- Steps 05–07; Phase 5.2.

## Common issues

- Names copied into summaries text by the generative level; deletion must
  also rewrite or remove those summaries (flag them for regeneration).
