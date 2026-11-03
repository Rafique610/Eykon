# Source of the head documents

The Word files in `docs/documents/` are generated. **Edit the JSON here, not the .docx**, then rebuild;
a change typed into Word is lost at the next rebuild.

| File | What |
|---|---|
| `heads/head<N>.json` | All text and tables of one head document |
| `build.js` | Turns one JSON file into one .docx (docx-js) |
| `build-all.js` | Rebuilds all eight into `docs/documents/` |
| `render.ps1` | Optional check: saves a .docx as PDF through Word, to look at the pages |

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
`{"table": {"cols": [...], "widths": [...], "rows": [[...]]}}` or `{"note": "..."}` (shaded box).
`**bold**` works inside any text.

## Updating a supervisor question (Head 2 section 2)

1. Find the question's `h3` block and the table under it.
2. Change **Status** (Answered / Partly / Open), rewrite **Answer** with the new numbers, add the
   result file to **Evidence**, update **Next / card** and **Last updated**.
3. Update the same question's row in the overview table at the top of the section.
4. Never delete an old finding: if a new run disagrees, say so in the Answer.
5. Rebuild, open the .docx, check the page, commit the JSON and the .docx together.
