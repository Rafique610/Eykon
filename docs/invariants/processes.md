# processes.md — plans, ADRs, cadence, README, session memory

## Creating a plan

When the user asks for a plan:

1. Explore the whole codebase and/or whatever's being built — read
   existing code, patterns, docs, conventions. Don't skip this to save
   time; a plan built on a wrong assumption costs more later.
2. Produce ONE big detailed plan.
3. Break it into numbered steps (`01-...`, `02-...`), each small, testable,
   with clear dependencies.
4. Each step doc includes: What / Why / How to implement / Open decisions
   (if any) / Verification / Files changed / Dependencies / Common issues.
   - Open decisions: anything in this step that's a genuine judgment call,
     not something to just pick and move on. For each one, give 2-3
     concrete options and a one-line research note per option (a real
     trade-off, not a restatement of the option) — enough for the user to
     decide without having to go research it themselves. Skip this field
     entirely on steps where nothing is actually open; don't manufacture a
     decision just to fill the section.
5. Save plan docs under `docs/plans/` (or `docs/additional/` if that's the
   repo's existing convention).
6. Work the plan using the cadence in AGENTS.md ("Working one step at a
   time").

## README maintenance

Update `README.md` on every step, before handing off for approval — new
capabilities, file paths, terminal commands. Every commit should naturally
include an up-to-date README; don't leave it for the end. Keep it synced
with the live state of the codebase (architecture, folders, commands).

## ADRs (new — not in either source doc, worth adopting)

Neither prior doc actually defined an ADR process, even though "discuss the
design pattern with the user first" (security.md, core.md) implies
decisions worth recording. Suggested lightweight version: when a
design-pattern or architecture decision gets discussed and settled with the
user, write a short paragraph under `docs/adr/` (or as a note at the top of
the relevant plan step) — what was decided, why, what was ruled out. Drop
or adjust this if it turns out to be more overhead than it's worth.

## No decision without evidence

Added 4 November 2026, after the supervisor's review: "the group has a
tendency to make design decisions based on assumptions rather than real
research."

- Research comes **before** the decision, never after it to defend it. Until
  the evidence is in, a choice is a **proposal**, and the docs, flows and
  cards must call it that.
- Every design decision records: the options found (each with a source:
  paper, docs page, repo or our own test), what we tested ourselves, the
  numbers, what was ruled out and why, and who took part. That record is the
  ADR.
- Every number a decision rests on (a limit, a target size, a threshold) has
  a stated source or our own measurement. "Feels right" is written down as
  an assumption, with a card to check it.
- "We read online that X fails" is not evidence. Run X on the real device
  and keep the exact error.
- Decisions are taken with the team: the researcher (Taha) brings the
  options, the evaluator (Zara) brings the data, and the lead decides with
  both. The ADR names all three. A teammate can block a decision by showing
  the data doesn't support it.
- If you find an older decision that rests on an assumption, don't quietly
  fix it: list it as a gap with a card.

## Show-ready proof

The supervisor does not accept "an automated test passed." He wants the
real data and outcome, good or bad, shown on the spot. So every result is
kept as something that can be opened in a meeting in under a minute:

- **Raw output**, unedited: logcat, CSV or console text, with device, date
  and commit hash in it.
- **A graph or table** made from that raw output, and the script that made
  it, so the figure can be redrawn from the data.
- **A screenshot or screen recording** for anything that happens on screen
  or on a phone (the error message, the app result).
- **One line of verdict**, including bad outcomes: "fails at 300k: out of
  memory" is a result and stays in the record.
- All of it is linked from the card's comment and from the head's document
  (`docs/documents/`), so in a demo you open the card or doc and the proof is
  one click away. A result that exists only in chat or someone's memory
  doesn't count.

## Head documents are filled while the work runs

Each pipeline head has a Word document in `docs/documents/`, generated from
`docs/documents/source/heads/head<N>.json` (see that folder's README). It is
the record we open in a supervisor meeting, so it's kept current as we go,
not written up afterwards.

- **Same step, same time.** When a run or test on a head produces a finding,
  update that head's JSON and rebuild the document in the same step as the
  card comment. A card doesn't go to review until its head document shows
  the result.
- **Every part covers:** the approach (what we tried and why, and the options
  we ruled out), what we did (steps, exact commands, devices, commit), the
  outcome (a table of the numbers, a graph, screenshots, links to the raw
  files in `docs/results/`, and a one-line verdict, good or bad), and what's
  next (the card that follows).
- **Data stays with the evidence.** Raw files go in `docs/results/<area>/`;
  the document shows the table made from them and links the file. Each graph
  is kept with the script and data that drew it, so it can be redrawn.
- **Graphs are redrawn, not stacked.** When new data comes in (a rerun, a
  new phone, a protocol run replacing a trial run), rerun the figure script:
  it writes the same file name, so the document picks up the new image and
  the old one is gone. The caption says which runs the graph shows. A run
  that's dropped from a graph is named in the part's text as superseded,
  and why.
- **Order by pipeline position, not by date.** Parts sit where they fit in
  the flow (setup → storage → intake → processing → … → search → output),
  so reading a document from top to bottom follows the pipeline. Dates go
  only in each part's "Last updated" line and in the change history, never
  in the section order. A later finding goes into the part it belongs to,
  not at the end.
- **Explain every name you use.** If a result names a method, variant or
  setting ("faster loop", "blob_disk_dot", "diskMax"), the same document
  says what it is in plain words, how it differs from the alternative
  (a side-by-side table helps), where it lives in the code, and a short
  code excerpt when the difference is in the code. A reader a week later,
  or the supervisor in a demo, must not need the chat or the source to
  understand a table or a graph.
- **Never overwrite a finding.** If a new run disagrees with an older one,
  keep both and say which is current and why.

## Session memory log — `.memory/`

Shared memory for the agent AND the user. This is what makes progress
visible without re-deriving it from chat history.

- One folder per day: `.memory/<date>/`, e.g. `.memory/15-september-2026/`.
- One single file per day: `tasks.md`. Never split into multiple files per
  feature.
- Sequential: each new task/step/feature is appended below the previous
  rows, in chronological order, as work happens.
- Every entry:
  - Date in words: `15 September 2026` (not `09/15/2026`).
  - Time in 12-hour AM/PM, with time zone AND UTC:
    `1:48 AM (UTC+05:00 · 20:48 UTC)`. Note which user/region did the work
    if that's ever ambiguous.
  - Real wall-clock time captured at the moment of writing — never guessed
    or fabricated. If a past entry wasn't captured live, mark it
    `(~ approx.)` and go exact from the next entry on.
- A task board table so the day is scannable at a glance: a one-line day
  verdict, a bold summary row (X done / Y approved / Z changed), a status
  badge per task (✅ Approved / 🔄 In progress / ⚠️ Needs changes).
- Update the table on every iteration — after every chat turn, not batched.
  Log what was assigned that day, how many got approved, how many needed
  changes and what changed.
- Each row carries enough detail to reverse the change later from the entry
  alone: file paths, component names, the exact thing added/changed. If the
  user says "reverse that," it should be undoable from the row without
  asking what it meant.
- A dedicated section logging every change to the invariants docs that day
  (this replaces "every change to INSTRUCTIONS.md" now that it's split into
  `docs/invariants/`): both rules the user explicitly asked to add/change,
  and any rule the agent added on its own initiative from something the
  user said. For each:
  - Changed: which doc + section, and what was added/edited, as a plain
    reversible sentence — e.g. "Added to backend.md: request schemas
    mandatory on all endpoints."
  - Why/trigger: what the user said that caused it, one line.
  - To revert: the exact action to undo it.
- Keep it readable for both the AI and a human — tables, clear spacing, no
  ambiguity.
- `.memory/` is git-ignored. Never commit it or share it publicly; share
  with teammates only if they ask.
