# Source of the head documents

The Word files in `docs/documents/` are generated. **Edit the source here, not the .docx**, then
rebuild; a change typed into Word is lost at the next rebuild.

There are two kinds of head document:

- **Defense doc** (Head 2 so far): Parts A–E (the card, the story, hard questions, evidence,
  words and gaps), written for a review. Layout and rules: `../HEAD-DOC-TEMPLATE.md`. Each defense
  doc is one script, `head<N>-defense.js`, with its text in arrays at the top of each Part.
- **Record doc** (Heads 1 and 3–8 until they get a defense doc): numbered sections from
  `heads/head<N>.json`, turned into Word by `build.js`.

| File | What |
|---|---|
| `head2-defense.js` | The Head 2 defense doc: text, tables, and which graphs it shows |
| `heads/head<N>.json` | All text and tables of one record doc |
| `build.js` | Turns one JSON file into one record doc (docx-js) |
| `build-all.js` | Rebuilds every head document into `docs/documents/` |
| `render.ps1` | Optional check: saves a .docx as PDF through Word, to look at the pages |
| `figures/*.py` | Graph scripts; each reads the raw files in `docs/results/` and rewrites its PNGs here |
| `figures/*.png` | The graphs the documents show (generated: rerun the script, don't edit) |

## Rebuild

```
cd docs/documents/source
npm install
npm run build
```

Close the .docx in Word first, or the build cannot overwrite it.

## Record doc JSON shape

Each section is `{ "title": ..., "blocks": [...] }`. A block is a plain string (paragraph),
`{"h3": "..."}`, `{"bullets": [...]}`, `{"steps": [...], "ref": "unique-name"}` (numbered list),
`{"table": {"cols": [...], "widths": [...], "rows": [[...]]}}`, `{"note": "..."}` (shaded box),
`{"image": "figures/x.png", "caption": "...", "width": 0.8}` (PNG or JPEG, path relative to this
folder, `width` = share of the text width, default 1) or `{"code": ["line", ...]}` (a short code
excerpt in monospace). `**bold**` works inside any text except code.

## Graphs

New data comes in → rerun the graph script → rebuild. The script writes the same file names, so
the document shows the new graph and the old one is gone; say in the text which runs it shows.

```
uv run docs/documents/source/figures/vector_sweep.py    (Head 2 vector graphs)
uv run docs/documents/source/figures/search_speed.py    (Head 7 search graphs)
```

Run them from the repo root. `vector_sweep.py` reads the real-vector runs in
`docs/results/vectors/` (`*-sweep-real.csv`, `*-memory.csv`); a new phone appears on its own, and
if one phone has several files the newest wins and the older ones are printed as superseded.

## Updating a hard question (defense doc, Part C)

1. In `head<N>-defense.js`, find the question's line in the `Q` array.
2. Change its status (Answered / Partly / Open), rewrite **Say this** with the new numbers, point
   **Show** at the evidence item (E#), update **If they push** and **Closes with**.
3. New table or graph → add it to Part D as the next E number. If a number in Part A changes,
   change Part A too, and the date on the cover.
4. Never delete an old finding: if a new run disagrees, say so and keep the old evidence.
5. Rebuild, open the .docx, check the page, commit the script and the .docx together.
