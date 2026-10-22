You are going to produce (1) a complete technical walkthrough of this repository and (2) an interactive visual flow built from it. The pipeline is large, so work stage by stage, write everything to disk as you go, and keep a progress file so work can resume after a context reset.

## Ground rules
- Read the actual code. Never infer behavior from file names or the README alone.
- Every claim cites file paths and function/class names (line ranges where useful).
- Tag every "why was this chosen" explanation as one of:
  [DOCUMENTED]: stated in README, comments, docs, commit messages, PRs, or issues (cite the source)
  [INFERRED]: your reasoning from the code (state the evidence)
  [UNKNOWN]: cannot be determined; add it to the open-questions list
  Never present an inferred reason as a documented one.
- Flag dead code, unused files, ambiguity, TODOs, and suspected bugs instead of explaining them as if they were active.
- Use subagents for per-stage and per-module work. Every subagent must follow the exact same output formats defined below.
- Maintain /docs/walkthrough/PROGRESS.md as a checklist of every phase and stage (not started / in progress / done / verified). Update it after each unit of work. On start, read it first and resume from it if it exists.

## Phase 0: Inventory and stage decomposition (STOP for my approval after this)
1. Map the repo: directory tree, languages, build system, dependencies with versions, entry points, configs, scripts, tests, datasets, model/weight files. List generated files, lockfiles, and vendored code as "skipped".
2. Read git log for major decisions (library swaps, migrations, "switch to X" commits) and save notes for the decisions phase.
3. Split the pipeline into 5-15 top-level stages (separate offline/training flows from runtime/inference flows if both exist). Write /docs/walkthrough/00-overview.md containing: what the project does, how to run it, the stage list (id, name, one-line purpose, entry files), the stage-to-stage data handoffs, and a draft Mermaid overview flowchart.
4. Create PROGRESS.md and show me the stage list and plan. Wait for my go-ahead before Phase 1.

## Phase 1: Per-stage deep dives (one stage at a time)
For each stage, write /docs/walkthrough/stages/<stage-id>.md with these sections:
1. Purpose and trigger: what starts this stage and why it exists
2. Input: type, shape, dtype, format, units, a concrete example, and where it comes from
3. Processing, step by step: which files/functions run in order, the algorithm or technique at each step, key parameters/thresholds and where they are configured, time/space complexity or performance notes (batching, caching, SIMD, GPU/CPU, memory layout, quantization) where relevant
4. Models and algorithms used: name, variant/version, source (pretrained, custom, library), file where defined or loaded, purpose, input/output specs, architecture or algorithm steps, loss/optimizer/hyperparameters and training details if applicable
5. Output: type, shape, format, concrete example, and where it goes next
6. File reference: EVERY source file in this stage. For each file give path, one-line purpose, main classes/functions (what each does, parameters, return values, side effects, which algorithm/model it implements), what calls it and what it calls, and non-obvious details (edge cases, assumptions, hacks, TODOs, bugs, performance traps)
7. Design decisions for this stage: decision, where it shows in code, why (tagged), realistic alternatives not chosen with their trade-offs (accuracy, latency, memory, complexity, ecosystem, constraints), and the consequences or limitations of the choice
8. Open questions: specific questions for the author

Also write the machine-readable twin of each stage at /docs/walkthrough/flow/stages/<stage-id>.json (schema below). Mark the stage done in PROGRESS.md only when both files exist.

## Phase 2: Cross-cutting documents (after all stages are done)
- 02-models-and-algorithms.md: one consolidated inventory of every model/algorithm, with links to the stage docs that use it
- 04-data-and-config.md: all data formats and schemas (inputs, intermediates, outputs, on-disk formats), every config option and what it changes, environment variables, how data is stored and loaded
- 05-design-decisions.md: the full decision log (chosen option, why with tag, alternatives and trade-offs, consequences), plus the constraints that likely drove decisions (hardware, deadlines, dataset size, deployment target) with evidence
- 06-open-questions.md: every [UNKNOWN] as a specific question I can answer, doc-vs-code inconsistencies, dead code, risky areas, potential bugs, and a suggested reading order for a newcomer

## Phase 3: Visual flow data
Define the schema and use it for every stage file:
- node: id, label, type (stage | file | model | algorithm | data-store | external), parent stage id, file path(s), one-line purpose, input {type, shape, format, example}, output {type, shape, format, example}, algorithm/model and key parameters, complexity/performance notes, decision summary with its tag, link to the matching section in the markdown docs
- edge: from, to, data carried (type and shape), flow type (offline/training or runtime/inference)
Then create /docs/walkthrough/flow/index.json holding the top-level stages, the stage-to-stage edges, and a list of the stage files.
Write a validation script /docs/walkthrough/validate_flow.py that checks: every source file in the stage docs appears in at least one node; every edge connects existing nodes; no required field is empty; every node links to an existing doc section. Run it and fix everything it reports.

## Phase 4: Build the interactive visual
Write a build script /docs/walkthrough/build_flow.py that reads flow/index.json plus all stage JSONs and generates ONE self-contained /docs/walkthrough/flow.html with the data embedded inline. It must work by double-clicking the file: no server, no build step for me, no external network resources (if you need a layout library, vendor it inline; otherwise write a simple layered layout yourself).
Requirements:
- Level 1, overview: the main stages as a left-to-right flow, edges labeled with the data passed along them.
- Level 2, stage view: clicking a stage drills into that stage only, showing its files, models, and algorithms with a breadcrumb back to the overview. Never render the whole project as one graph.
- Click any node to open a side panel with everything known about it: purpose, input, output, algorithm and parameters, complexity, decision rationale with its tag, and a link to the doc section.
- Color-code node types. Show offline/training paths and runtime/inference paths in visibly different styles. Give [INFERRED] and [UNKNOWN] items a distinct badge.
- A search box, filters (node type, stage, flow type), and a legend.
- "Trace an input" mode: I pick an entry point and the page highlights the nodes and edges it passes through in order, showing the input and output at each step.
- Light and dark mode, readable on a laptop screen.
Also export /docs/walkthrough/flow-overview.mmd (Mermaid) for the overview, and flow-overview.svg via Graphviz or D2 if installed (otherwise skip and tell me).

## Final verification
1. Re-check at least 15 random claims across different stages against the code and fix any errors.
2. Re-run validate_flow.py and confirm it passes.
3. Give me a short summary: what was produced, how to open flow.html, what you are least confident about, and which three files to read first.

Start with Phase 0 now. Show me the stage list and plan, then wait.