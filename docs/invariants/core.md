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
- Established pattern: raw `sqlite3` with parameterized queries (not ORM — this is the actual project convention despite INSTRUCTIONS.md mentioning ORM).

## UI/UX Skill Routing

- UX review/polish/audit → **impeccable** skill.
- Visual redesign/overhaul → **ui-ux-pro-max** skill.
- Backend security → **backend-security-coder** skill.
- If a skill is missing, tell the user how to install it.

## Phase Parity

- When porting features across phases (desktop → Android), derive decisions, parameters, and constraints directly from earlier phase implementations.
- Keep Phase 1 constants (chunk size 256, overlap 40, FTS5 config) unchanged unless explicitly approved.
