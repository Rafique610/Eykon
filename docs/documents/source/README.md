# Source of the head documents

The Word files in `docs/documents/` are generated. **Edit the JSON here, not the .docx**, then rebuild;
a change typed into Word is lost at the next rebuild.

| File | What |
|---|---|
| `heads/head<N>.json` | All text and tables of one head document |
| `build.js` | Turns one JSON file into one .docx (docx-js) |
| `build-all.js` | Rebuilds all eight into `docs/documents/` |
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

## JSON shape

Each section is `{ "title": ..., "blocks": [...] }`. A block is a plain string (paragraph),
`{"h3": "..."}`, `{"bullets": [...]}`, `{"steps": [...], "ref": "unique-name"}` (numbered list),
`{"table": {"cols": [...], "widths": [...], "rows": [[...]]}}`, `{"note": "..."}` (shaded box) or
`{"image": "figures/x.png", "caption": "...", "width": 0.8}` (PNG or JPEG, path relative to this
folder, `width` = share of the text width, default 1) or `{"code": ["line", ...]}` (a short code
excerpt in monospace). `**bold**` works inside any text except code.

## Graphs

New data comes in → rerun the graph script → rebuild. The script writes the same file names, so
the document shows the new graph and the old one is gone; say in the text which runs it shows.

```
uv run docs/documents/source/figures/vector_sweep.py   (from the repo root; Head 2 sweep graphs)
```

`vector_sweep.py` reads every `docs/results/vectors/*-sweep.csv`. A new phone appears on its own;
if one phone has several sweep files, the newest wins and the older ones are printed as superseded.

## Updating a supervisor question (Head 2 section 2)

1. Find the question's `h3` block and the table under it.
2. Change **Status** (Answered / Partly / Open), rewrite **Answer** with the new numbers, add the
   result file to **Evidence**, update **Next / card** and **Last updated**.
3. Update the same question's row in the overview table at the top of the section.
4. Never delete an old finding: if a new run disagrees, say so in the Answer.
5. Rebuild, open the .docx, check the page, commit the JSON and the .docx together.
