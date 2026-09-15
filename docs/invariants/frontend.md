# Frontend Invariants (Streamlit)

Rules for all Streamlit UI work in this project.

## Framework

- Streamlit (`>=1.35.0`). No other frontend framework.
- Entry point: `src/ui/app.py`, launched via `main.py` subprocess or `streamlit run src/ui/app.py`.

## Layout

- `st.set_page_config(layout="centered")` with sidebar navigation.
- Pages via `st.radio()` in sidebar: `📝 Add Memory`, `❓ Ask Question`, `🎬 Process Video`.
- Sidebar always shows: live memory count, model status, active RAG pipeline config.

## Conventions

- Embedder cached via `@st.cache_resource`.
- Phased spinners (`st.spinner`) for slow operations to keep user informed.
- Confirmation echoes for stored data.
- Retrieved memories shown with scores (RRF, semantic, BM25).
- No new dependencies — only `streamlit` (already in `pyproject.toml`).

## UX Engagement

- Always think from the end-user's perspective.
- UI should serve the story, not just render data.
- Use **impeccable** skill for polish/audit, **ui-ux-pro-max** for redesigns.

## Real Data Only

- Every number shown in the UI comes from a real DB query or computation.
- Never show mock/placeholder metrics.
