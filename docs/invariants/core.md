# Core Invariants

Rules that hold for **every task**, regardless of stack or feature.

## Folder Structure

- Feature-based: `src/<feature>/` (e.g. `src/memories/`, `src/assistant/`, `src/ui/`, `src/vision/`).
- Never horizontal layering (`src/capture/`, `src/storage/`).
- Each feature owns its models, DB access, services, helpers.

## File Size

- Max ~300 lines per `.py` file. If exceeded → split or apply a design pattern.
- Inform the user which pattern was used and why.

## Real Data Only

- **Never** show fabricated/mock/placeholder data in UI, API responses, or dashboards.
- Every rendered number must come from a real source (DB query, file, service).
- If a metric cannot be measured, compute it honestly, show only real parts, or omit — never invent.

## Ponytail Ladder (Strictly Active)

Always write the laziest solution that works. Follow this order:

1. **Does this need to exist at all?** (YAGNI)
2. **Already in this codebase?** Reuse existing functions/types/patterns.
3. **Standard library does it?** `sqlite3`, `dataclasses`, `json`, `pathlib`.
4. **Native platform feature?** Use it.
5. **Already-installed dependency?** Use it — never add packages without explicit need.
6. **Can it be one line?** Make it one line.
7. **Only then:** write the minimum code that works.

No unrequested abstractions. No factories for one product. No speculative interfaces.
Bug fixes address root causes. Shortest working diff wins.

## Configuration

- Always through Pydantic `Settings` in `src/config.py` with `MEMORY_` prefix.
- Never read environment variables directly in code.

## Database

- Local SQLite at `data/memories.db`.
- Fully parameterized queries (`?`), idempotent `init_db()`.
- Raw `sqlite3` with parameterized queries. No ORM (confirmed 12 October 2026; the old INSTRUCTIONS.md ORM rule is retired).
- Anything the database needs must also work on Android. No loadable SQLite extensions: the phone's SQLite cannot load them.
- Vectors are float32 BLOB columns in normal tables. Search loads a vector table into memory once and uses the dot product; never read every vector from SQLite on each query (decided 12 October 2026, measurements in `docs/results/2026-10-12-eyko-31-vector-storage.md`).

## UI/UX Skill Routing

- UX review/polish/audit → **impeccable** skill.
- Visual redesign/overhaul → **ui-ux-pro-max** skill.
- Backend security → **backend-security-coder** skill.
- If a skill is missing, tell the user how to install it.

## Phase Parity

- When porting features across phases (desktop → Android), derive decisions, parameters, and constraints directly from earlier phase implementations.
- Keep Phase 1 constants (chunk size 256, overlap 40, FTS5 config) unchanged unless explicitly approved.
- Retrieval on the phone is the laptop's retrieval, not a simpler one (13 October 2026): keyword search scored with BM25, dense vector search, the two lists fused with RRF (k = 60), the same pool and top-K sizes, and the later steps the laptop has (query expansion, re-ranking). Where the phone lacks a building block (its SQLite has fts4 without a `bm25()` function), build the same maths on the phone and check it against the laptop's numbers; do not drop the step.

## Destructive Operations & File Safety
- **Never blindly overwrite JSON/data files:** Always read existing data, parse it, merge updates, and write back. Overwriting a file from an empty state is strictly prohibited unless explicitly requested.
- **Never run destructive actions silently:** Deleting files, wiping databases, or resetting states requires explicit user confirmation before execution.
