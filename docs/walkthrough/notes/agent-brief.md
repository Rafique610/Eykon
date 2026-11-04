# Brief for a stage deep-dive subagent

You write the walkthrough of **one** stage of the Eykon repository
(`/home/tahagpt/Documents/fyp/Eykon`). Your stage id is given in your task
(for example `s04-scene`). You produce exactly two files:

1. `docs/walkthrough/stages/<stage-id>.md`: the stage doc
2. `docs/walkthrough/flow/stages/<stage-id>.json`: its machine-readable twin

Fifteen agents do this in parallel for fifteen stages, so the format must be
exactly the same everywhere.

## Read first, in this order

1. `ANALYSIS.md` (repo root): the owner's ground rules. They bind you.
2. `docs/walkthrough/00-overview.md`: §1, §4 (the stage list), §5
   (handoffs between stages).
3. `docs/walkthrough/stages/_TEMPLATE.md`: the doc format, section by
   section. The comments in it are instructions.
4. `docs/walkthrough/flow/schema.json`: the JSON format (`$defs/stage_file`,
   `$defs/node`, `$defs/edge`).
5. `docs/walkthrough/notes/file-map.md`: your stage's **Primary**, **Data
   files** and **Also read** lists, the **Shared node ids**, the **Fixed
   file-node ids** and the naming rules.
6. `docs/walkthrough/notes/flags.md`: known problems. Confirm or clear the
   ones listed for your stage.
7. `docs/walkthrough/notes/git-decisions.md`: where the reasons for past
   decisions are written.

Then read **every Primary file of your stage completely**, not excerpts. Read
the parts of the "Also read" files that your stage uses, and the
`docs/results/` files that justify your stage's constants.

## Hard rules

- **Only write your two files.** Do not edit source code, `notes/*`,
  `PROGRESS.md`, `00-overview.md`, the template, the schema, the validator or
  any other stage's files. Report anything that should change there in your
  final message instead.
- **Git:** read-only commands only (`git log`, `git show`, `git blame`).
- **No installs, downloads, Gradle runs or long jobs.** Small `python3`
  snippets to count or check things are fine.
- **Line numbers are per file.** Use the Read tool or `grep -n` on one file.
  Never run `cat -n` on several files at once: it numbers lines
  continuously across files and gives wrong line numbers.
- **Never infer behaviour from names.** Every claim cites a repo-relative
  path and a symbol, with line numbers where useful.
- **Why-tags:** every "why" carries exactly one of `[DOCUMENTED]` (cite the
  doc, comment or commit), `[INFERRED]` (give the code evidence) or
  `[UNKNOWN]` (add a question `Q-sNN-n` to §8.1 and cite its id). Never
  present an inferred reason as documented. A code comment that states the
  reason counts as documented: cite `path:line`.
- **Numbers** (timings, accuracy, sizes, counts) come only from code
  constants or `docs/results/` files (name the file, and the device: laptop,
  Pixel 9 Pro XL, Samsung A32, Infinix Note 12). Otherwise write "not
  measured". Do not round differently from the source.
- **Flag, don't excuse:** dead code, unused files, stubs, TODOs, ambiguity,
  suspected bugs and doc-vs-code mismatches go in §8.2 with evidence. Do not
  describe them as working features.
- **Plain, exact English.** Short sentences. No praise or marketing words.
  Tables where they help. Explain an acronym the first time it appears.

## The stage doc

Follow `stages/_TEMPLATE.md`: keep the eight numbered `##` headings exactly,
delete the template comments, and fill the header block (date 22 October
2026, commit `89b4da8`). In §6, give every Primary file (tests too, shorter) its own level-3
heading whose whole text is the full repo-relative path in backticks:

```
### `src/video_memory/schema.py`
```

Depth over breadth: a newcomer should be able to follow every step and every
constant.

## The JSON twin

- `schema_version` 1. A `stage` object (a node of type `stage` with
  `platform`, `entry`, `exit`), `nodes`, `edges`.
- **Every required field is filled.** Write `"n/a: <why>"` when a field
  does not apply, never `""` or a bare `"n/a"`.
- **Node types:** `file` (one per non-test Primary file; tests may be one
  node per file or grouped as `tests-<group>`), `model` (one per model this
  stage runs, with `key`), `algorithm` (one per technique worth seeing, with
  its parameters and their sources), `data-store` (tables and stored files),
  `external` (people, datasets, outside services such as Hugging Face, the
  Android photo picker).
- **Keys for models and shared techniques** (reuse these; invent new ones in
  the same style if needed): `mobileclip-s2-image`, `mobileclip-s2-text`,
  `bge-small-en-v1-5`, `yolox-tiny`, `dfine-s-obj365`, `yoloe-11l`,
  `gemma-4-e2b`, `ms-marco-minilm-l6`, `smolvlm-500m`, `owlv2`,
  `yoloe-11s`, `whisper-tiny`, `android-speech-recognizer`, `dhash-64`,
  `laplacian-variance`, `cosine-dot`, `rrf`, `bm25`, `clip-bpe`,
  `wordpiece`, `letterbox`, `nms`.
- **Shared ids:** if your stage owns any **Shared node ids** or **Fixed
  file-node ids**, define every one of them with exactly that id. Never
  redefine another stage's id. Point your edges at them.
- **Edges carry data**, from producer to consumer: what is passed (`label`,
  short), and `data.type` / `data.shape`. Put an edge in your file when at
  least one end is your own node. Never write an edge whose two ends both
  belong to other stages. Model nodes sit on the data path: input → model →
  output.
- **`flow`** is when the data moves: `runtime` while the app or the laptop
  prototype runs (loading a model file or an asset counts as runtime);
  `offline` during lab work (export, benchmark, evaluation). Nodes of offline
  stages are `offline`.
- **`doc`** links into your own stage doc: a file node to its §6 heading, a
  model or algorithm to its §4 subsection, a data store to the §2, §3 or §5
  place that describes it, the stage node to `#1-purpose-and-trigger`. Get
  exact anchors with
  `python3 docs/walkthrough/validate_flow.py --anchors stages/<stage-id>.md`.
- **`decision`** on every node: the choice this node embodies, tagged as
  above. Use `[UNKNOWN]` honestly, with a question id.
- `status`: `unused` for dead code, `stub` for placeholders, `legacy` for
  kept-but-superseded paths. `flags` for problems.
- `entry`: the node(s) where data enters your stage. `exit`: where it leaves
  (often a shared data store). Traces follow these.
- Size guide: about 12 to 40 nodes.

## Check, then report

Run `python3 docs/walkthrough/validate_flow.py --stage <stage-id>` and fix
every problem it prints until it prints `OK`. Then re-read three of your own
claims against the code.

Your final message (under 400 words) to the coordinator:

1. The two files written, and the validator's last line.
2. **New flags** not already in `notes/flags.md`: one line each, with kind
   and `path:line` evidence. Then which listed flags you confirmed or
   cleared (by id).
3. How many `[UNKNOWN]` items and questions you wrote.
4. Anything that contradicts `00-overview.md` or `notes/file-map.md`, or
   that you could not determine.
