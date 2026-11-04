# Security Invariants

Rules for credentials, database access, and secrets management.

## Credentials

- **Never** hardcode credentials anywhere — not in code, config files, Docker, or scripts.
- All secrets sourced from `.env` / `.env.local` via Pydantic `Settings`.
- Docker Compose references `${VAR}` syntax, never inline values.

## Environment Variables

- Never use `os.getenv()` directly. Always route through `Settings` class in `src/config.py`.
- Env prefix: `MEMORY_`.
- `.env.example` documents all available variables with safe defaults.

## Database Security

- Parameterized queries only (`?` placeholders). Never string-interpolate SQL.
- SQLite file at `data/memories.db` — not committed to git.

## Error Handling

- Never leak sensitive info in error messages or logs.
- Fail secure — if authentication/authorization fails, deny by default.

## Secrets in Output

- Never expose credentials in terminal output, UI, or API responses, even for local/test credentials.
