# Eykon Head defense doc: template and rules

Use this file to write or update the defense doc for any Head (one .docx per Head).
The finished example is `Head-2-Setup-and-storage.docx`. Copy its look and its order exactly.

Purpose: the owner reads this doc the night before a review and shows it to the professor.
It must answer three things fast: **what we did, why, and what came out**. It must also hold the proof (tables and graphs) to show on the spot.

---

## Writing rules (apply everywhere)

- Plain language. Write it the way you would explain it to a smart friend who is not on the project.
- Short sentences, one idea each. If a sentence needs a semicolon, split it.
- Every number in Parts A, B and C must point to an evidence item in Part D (`Show: E3`).
- Explain each technical word the first time it appears, or add it to the glossary (Part E).
- Do not paste logs, commands or long code into Parts A–C. File paths go in the `Source:` line under each evidence item.
- Be honest about gaps. An "Open" status with a plan is better than a vague "Answered".
- Never delete an old finding. If a newer run disagrees, say so and keep both.

---

## Cover (page 1)

- Eyebrow: `EYKON · DEFENSE NOTES · HEAD <n> OF THE PIPELINE`
- Title: the Head's short name (e.g. "Setup & storage")
- One-line subtitle: what this Head decides or builds
- Small table: **Last updated**, **Overall status** (1–2 sentences), **Cards** (each card number with a 2–4 word name)
- "How to use this document" table: Part A–E, one line each

## Part A · The card (aim for 1–2 pages)

1. **In one breath**: 3–4 sentences in a shaded box. Bold the 2–3 phrases that matter most. Someone who reads only this should get the whole Head.
2. **Where it sits in the pipeline**: one row of pipeline stages with this Head highlighted, then one sentence: what comes before it and what depends on it.
3. **What · Why · Result**: three columns, 2–3 sentences each.
4. **Numbers to remember**: exactly 4 tiles. Each has a big number, a few words of meaning, and `Show: E#`.
5. **Decisions and the reason for each**: table with the columns Decision | Because | Show.
6. **Weak spots: say these before they find them**: 3–5 lines, each with a status chip and a card number.

## Part B · The story

Numbered steps in the order things happened, usually 6–10. Each step has:
- a small label: `QUESTION`, `RULE SET BEFORE TESTING`, `TEST · <date> · <card>`, `DECISION`, `RE-CHECK`, `IMPROVEMENT`, `LIMIT FOUND` or `STILL OPEN`
- a bold one-line title that states the outcome ("sqlite-vec failed on the phone")
- 1–3 sentences
- `Show: E#` when there is evidence

Number colour: green for a step that passed or improved things, red for a failure or limit, blue for neutral steps.
The first step is always the question, and the last is always "Still open".

## Part C · Hard questions

1. **All questions at a glance**: table with the columns # | Question | Status | Closes with.
2. Then one card per question, grouped (A, B, C, D… with a heading per group). Each card has:
   - header row: `ID  Question  [STATUS]`
   - **Say this**: the first answer, 1–3 sentences, with the key number
   - **Show**: the evidence item(s) `E#`, or a file path, or "Nothing yet"
   - **If they push**: the honest caveat, or the next step
   - **Closes with**: card number(s)

Statuses: **ANSWERED** (green) = proof a person can check · **PARTLY** (amber) = some proof, gaps named · **OPEN** (red) = not tested yet.
Keep each card on one page.

## Part D · Evidence

Numbered E1, E2, … in the order the story uses them. Each item has:
- heading: `E# · <what was measured> (<date>)`
- **What it shows:** one sentence stating the conclusion
- the table and/or the figure (figures get a caption: `Figure n.` plus one sentence)
- `Source:` the repo file path, in small monospace text

Highlight the row that the argument rests on (light blue fill). Keep each table on one page.
End Part D with **Limits: how these numbers could mislead** (3–6 bullets).

## Part E · Words, gaps, upkeep

- **Words in plain language**: glossary table (Word | What it means here)
- **Open gaps for this Head**: Gap | What is missing | Card | Severity | Resolution
- **How to update this document** (the 4 rules below)
- **References**: key repo files

### How to update
1. When a card closes: change its status in Part C, rewrite "Say this" with the new numbers, add the new table or graph to Part D as the next E number, and change the date on the cover.
2. If the result changes a number in Part A, update Part A too. Part A must always match the latest evidence.
3. Never delete an old finding. If a new run disagrees, say so in "Say this" and keep the old table in Part D.
4. Add a step to Part B only for something that changed the direction of the work.

---

## Look (match Head 2)

- A4, 2 cm margins, Arial; body 10.5 pt, tables 9.5 pt
- Accent blue `#1F5F8B` for Part headings and the "in one breath" box
- Status chips: green `#1D7A4C` on `#E1F2E8` · amber `#8A5700` on `#FBF0D9` · red `#B0362B` on `#F9E3E0`
- Table header fill `#F1F4F7`, thin grey borders `#D3DBE2`
- Each Part starts on a new page. Footer: `Eykon · Head <n> · <name> · page <n>`
- The generator script used for Head 2 is `source/head2-defense.js` (docx-js). Copy it to `source/head<n>-defense.js`, swap the content arrays, and add the Head to `DEFENSE` in `source/build-all.js`.
- Graphs come from `source/figures/` (drawn by the scripts there from `docs/results/`), never from a temporary folder, so they can be redrawn when new data comes in.

## Prompt to give Claude Code for the next Head

> Read `HEAD-DOC-TEMPLATE.md` and `Head-2-Setup-and-storage.docx` as the example. Then write the defense doc for Head <n> from <existing doc / result files>, following the template exactly. Keep every table and figure from the source as Part D evidence. Rewrite everything else in plain language. Do not invent numbers: if something is not measured, mark it OPEN.
