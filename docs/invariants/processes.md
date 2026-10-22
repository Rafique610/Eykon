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
