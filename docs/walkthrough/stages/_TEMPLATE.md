# <stage-id>: <Stage name>

<!--
Template for every stage deep dive. Copy to stages/<stage-id>.md, keep the
eight numbered "##" headings exactly as written (the flow data links to
them), delete these comments when done.

Ground rules (ANALYSIS.md):
- Read the actual code. Never describe behaviour from file names, the
  README or memory. The code on disk at the commit in the header is the
  truth.
- Every claim cites a repo-relative path and a function/class name, with
  line numbers where useful: `android/app/src/main/java/com/eykon/memory/video/VideoDedup.kt:23` (`HASH_MAX`).
- Every "why" carries exactly one tag:
    [DOCUMENTED] stated in README, comments, docs, commit messages (cite it)
    [INFERRED]   your reasoning from the code (state the evidence)
    [UNKNOWN]    cannot be determined: add a question to §8 and cite its id
  Never present an inferred reason as a documented one.
- Numbers (timings, accuracy, sizes) come only from code constants or
  docs/results/ files (name the file and the device). Otherwise write
  "not measured".
- Dead code, unused files, stubs, TODOs, ambiguity and suspected bugs are
  flagged in §8.2, never explained as if they were active.
- Anchor slug rule (used by validate_flow.py): lower-case the heading text,
  drop every character that is not a-z, 0-9, space, "-" or "_", then turn
  each space into "-". "## 4. Models and algorithms used" becomes
  "4-models-and-algorithms-used"; "### 4.2 D-FINE S (Objects365)" becomes
  "42-d-fine-s-objects365". Avoid duplicate headings in one file.
-->

> **Flow:** runtime | offline · **Runs on:** phone | laptop | both ·
> **Pipeline position:** <e.g. stage 3 of 10 in `VideoPipeline.STAGES`> ·
> **Entry point:** `<path>` (`<function>`)
> Written <date> against commit `<short sha>`. JSON twin: `flow/stages/<stage-id>.json`.

## 1. Purpose and trigger

<!-- What starts this stage (a call, a job, a user action, a task command),
and why the stage exists. Cite the trigger in code. -->

## 2. Input

<!-- For each input: type, shape, dtype, format, units, a concrete example
(from a test, golden file, results doc or a constant), and where it comes
from (which stage, table, file). A table works well:
| Input | Type / dtype | Shape / units | Format | Example | From | -->

## 3. Processing, step by step

<!-- The files/functions that run, in order. One "###" per step:
### 3.1 <step name>
- **Code:** `<path>` (`<function>`), lines
- **Technique:** what it does, the algorithm
- **Parameters:** value, where configured (constant, Settings field, asset)
- **Cost:** complexity, batching, caching, threads, CPU/GPU, memory layout,
  quantization; measured timings only with their docs/results file. -->

## 4. Models and algorithms used

<!-- One "###" per model or algorithm (for example "### 4.1 YOLOX-Tiny").
For each give: name; variant/version; source (pretrained / custom /
library, with licence where known); file where defined or loaded; purpose;
input spec; output spec; architecture or algorithm steps; loss / optimizer
/ hyperparameters and training details if any (this project trains
nothing: say so, and say where the weights come from). -->

## 5. Output

<!-- Type, shape, format, a concrete example, and where it goes next
(which stage, table, file, screen). -->

## 6. File reference

<!-- EVERY primary file listed for this stage in notes/file-map.md, one
entry each, with the full repo-relative path in backticks as the heading:

### `android/app/src/main/java/com/eykon/memory/video/VideoDedup.kt`
- **Purpose:** one line.
- **Main classes/functions:** each with what it does, parameters, return
  value, side effects, and the algorithm/model it implements.
- **Called by:** ... **Calls:** ...
- **Non-obvious details:** edge cases, assumptions, hacks, TODOs, bugs,
  performance traps.

Tests get the same entry, shorter: what they check and against what data. -->

## 7. Design decisions

<!-- One "###" per decision:
### 7.1 <decision in a few words>
- **Decision:** what was chosen.
- **Where in code:** path and symbol.
- **Why:** [DOCUMENTED] ... (source) / [INFERRED] ... (evidence) /
  [UNKNOWN] see Q-<stage-id>-<n>.
- **Alternatives not chosen:** each realistic alternative with its
  trade-off (accuracy, latency, memory, complexity, ecosystem,
  constraints). Mark whether the project measured it (cite) or not.
- **Consequences / limitations:** what the choice costs or rules out. -->

## 8. Open questions

### 8.1 Questions for the author

<!-- Specific questions only the author can answer, each with an id:
- **Q-<stage-id>-1:** ... (context: path:line) -->

### 8.2 Flags

<!-- Dead code, unused files, stubs, TODOs, ambiguity, suspected bugs,
doc-vs-code mismatches. One line each with evidence (path:line), and the
flag id from notes/flags.md (F1 ...) when it is already listed there:
- **dead-code:** ... (`path:line`) -->

<!--
JSON twin (flow/stages/<stage-id>.json, schema flow/schema.json). Rules:
- Node ids: "<stage-id>/<local-id>", lower case, a-z 0-9 . _ - only.
- Node types: stage | file | model | algorithm | data-store | external.
  One "file" node per primary source file (tests may be grouped into one
  node that lists several files). One "model" node per model this stage
  runs, with "key" set (mobileclip-s2-image, mobileclip-s2-text,
  bge-small-en-v1.5, yolox-tiny, dfine-s-obj365, yoloe-11l, gemma-4-e2b,
  ...). One "algorithm" node per technique worth seeing (dHash, RRF, ...).
- Shared data stores (tables, frame files, ONNX files, assets) are NOT
  redefined: point edges at the ids in notes/file-map.md "Shared node ids".
  The owning stage defines them.
- Every node: all required fields filled; "n/a: <why>" when a field does
  not apply. "doc" links to the section that explains the node.
- Edges carry data (from producer to consumer), with flow runtime|offline.
- The "stage" object is a node of type "stage" with platform, entry, exit.

Example node:
{
  "id": "s03-keyframes/algo-dhash",
  "label": "64-bit difference hash",
  "type": "algorithm",
  "stage": "s03-keyframes",
  "flow": "runtime",
  "key": "dhash-64",
  "files": ["android/app/src/main/java/com/eykon/memory/video/FrameHash.kt"],
  "refs": ["android/app/src/main/java/com/eykon/memory/video/FrameHash.kt:16-17"],
  "purpose": "Cheap first test for near-duplicate frames.",
  "input": {"type": "grey picture", "shape": "9 x 8 after shrinking", "format": "...", "example": "..."},
  "output": {"type": "hash", "shape": "64 bits", "format": "hex text in frames.phash", "example": "..."},
  "algorithm": {"name": "dHash (difference hash)", "params": {"HASH_MAX": "6 bits (VideoDedup.kt:23)"}},
  "performance": "O(pixels) per frame; ...",
  "decision": {"summary": "...", "tag": "DOCUMENTED", "source": "VideoDedup.kt:11-20 comment"},
  "doc": "stages/s03-keyframes.md#4-models-and-algorithms-used"
}
-->
