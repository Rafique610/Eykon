# Phase 8 Step 10 — Demo Build, Demo Script and Backup

## What

A demo that cannot embarrass the project:

1. **Demo build**: release APK of the frozen system on both phones, with a
   pre-loaded memory database (a real recorded day, consented) and the live
   pipeline ready.
2. **Demo script** (about 5–7 minutes):
   - airplane mode on, shown to the panel;
   - live objects: put keys in a bag in front of the panel, ask "where are my
     keys?", show the evidence frame;
   - a question about the pre-loaded day ("what did I do after lunch?");
   - a pre-recorded meeting: show the summary with evidence links and "what
     did I agree to do?";
   - the LLM-optional toggle: same question at "Short facts" and "Smart
     answers", with the latency and cost difference visible;
   - privacy: pause, delete last minutes;
   - (optional) the Infinix running in low-end mode.
3. **Backup**: a screen recording of the full demo on both phones; a second
   charged phone; a laptop with the Streamlit pages and the same database.
4. **Checklist**: battery, storage, models, airplane mode, database loaded,
   brightness, Do Not Disturb, cables.

## Why

- Live demos fail at the worst time; the backup and checklist make failure
  survivable.
- The script shows each must-tier claim once, in the order of the slides.

## How to implement

1. Freeze the demo database; hash it.
2. Rehearse the script at least 5 times on both phones; time each part.
3. Record the backup video after a successful rehearsal.

## Open decisions

- **Which demo items to include** (from Gate 4: what holds on both phones).
- **Live meeting in the demo.** Options: (a) no — pre-recorded only (draft);
  (b) a 2-minute live mini meeting with a panel member's consent — impressive,
  risky; (c) only if the panel asks.

## You test this

1. Run the full demo for a friend who has never seen the app; ask them what
   they understood.

## How this number could be lying

- A rehearsed demo shows best-case behaviour; the slides say so and point to
  the measured results.

## Verification

- [ ] Demo works end to end in airplane mode on both phones, 5 rehearsals.
- [ ] Backup video and backup devices ready.
- [ ] Checklist written.

## Files changed

- [NEW] `docs/results/phase-8/demo-script.md`, demo checklist

## Dependencies

- Step 03 (frozen system).

## Common issues

- Phone updates installing the night before; disable automatic updates during
  the defense week.
