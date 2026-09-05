"""Streamlit UI — two-page Persistent Memory App.

Pages:
    📝 Add Memory  — capture and store a new memory chunk
    ❓ Ask Question — hybrid-search + on-device Gemma 4 answer

Design goals (impeccable + ponytail):
    - Sidebar always shows live status and memory count.
    - Phased spinners keep the user informed during slow operations.
    - Confirmation echoes exactly what was stored.
    - Retrieved memories are shown with RRF scores so retrieval is visibly working.
    - Zero new dependencies: only streamlit (already in pyproject.toml).
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path when invoked via `streamlit run`
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib
import time
import numpy as np
import streamlit as st

from src.config import Settings
import src.memories.search
importlib.reload(src.memories.search)
from src.memories.search import _sparse_search, search_memories

from src.assistant.helpers import check_model_available, get_model_status
from src.assistant.llm import generate_answer
from src.memories import (
    Embedder,
    count_memories,
    create_memories_from_text,
    init_db,
    save_memories,
)

# ── Constants ────────────────────────────────────────────────────────────────

MAX_TEXT_LENGTH = 5000

SAMPLE_MEMORIES = [
    "I have a dentist appointment on Tuesday at 3 PM with Dr. Smith.",
    "My brother's name is Ali and he lives in Lahore.",
    "I prefer tea over coffee, especially green tea in the morning.",
    "My final year project is about building a persistent memory app using on-device AI.",
    "I graduated from high school in 2020 and started university the same year.",
]

# ── Bootstrap ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Persistent Memory",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="expanded",
)

init_db()


@st.cache_resource(show_spinner="Loading embedding model…")
def _load_embedder() -> Embedder:
    """Load and cache the sentence-transformer embedder for the whole session."""
    return Embedder()


embedder = _load_embedder()

# ── Model status check (runs once on load) ───────────────────────────────────

model_ok, model_msg = get_model_status()

if not model_ok:
    st.error(
        "⚠️ **LLM model not found.** You can still add memories, "
        "but answering questions requires the model.\n\n"
        "Run this to download it:\n"
        "```bash\ntask pull-model\n```\n"
        "Then refresh this page."
    )

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🧠 Memory App")
    st.caption("Local-first · On-device AI · No cloud")
    st.divider()

    page = st.radio(
        "Navigate",
        ["📝 Add Memory", "❓ Ask Question"],
        label_visibility="collapsed",
    )

    st.divider()

    # Real-time count from DB — never fabricated
    total = count_memories()
    st.metric("Memories stored", total)

    if total == 0:
        st.info("No memories yet.\nAdd one to get started!", icon="💡")

    # ── Demo tools ──
    with st.expander("🧪 Demo Tools"):
        if total > 0:
            st.caption("Sample data disabled — memories already exist.")
            st.button("Load Sample Memories", disabled=True, use_container_width=True)
        else:
            if st.button("Load Sample Memories", use_container_width=True):
                with st.spinner("Loading 5 sample memories…"):
                    for sample in SAMPLE_MEMORIES:
                        records = create_memories_from_text(sample, embedder)
                        save_memories(records)
                st.success(f"Loaded {len(SAMPLE_MEMORIES)} sample memories!")
                st.rerun()

    st.divider()

    # Model status indicator
    if model_ok:
        st.markdown(
            f"<small style='color:#4a4'>🟢 ✅ {model_msg}</small>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<small style='color:#c44'>🔴 ❌ Model not found</small>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<small style='color:#888'>Embedder: BAAI/bge-small-en-v1.5<br>"
        "LLM: Gemma 4 E2B (on-device)</small>",
        unsafe_allow_html=True,
    )

    # Active RAG Pipeline details
    settings = Settings()
    with st.expander("⚙️ Active RAG Pipeline", expanded=False):
        st.markdown(
            f"<small style='line-height: 1.6;'>"
            f"• <b>Query Expansion:</b> {'🟢 ON' if settings.EXPAND_QUERY else '⚪ OFF'}<br>"
            f"• <b>Candidate Pool (Pool-K):</b> <code>{settings.POOL_K}</code><br>"
            f"• <b>Cross-Encoder Rerank:</b> {'🟢 ON' if settings.RERANK else '⚪ OFF'}<br>"
            f"• <b>Final Top-K:</b> <code>{settings.TOP_K}</code>"
            f"</small>",
            unsafe_allow_html=True,
        )


# ── Page 1: Add Memory ───────────────────────────────────────────────────────

if page == "📝 Add Memory":
    st.header("Add a New Memory")
    st.caption(
        "Paste any text — a note, appointment, preference, or fact. "
        "Long text is automatically chunked for best retrieval."
    )

    text = st.text_area(
        "Memory text",
        placeholder="e.g. My dentist appointment with Dr. Smith is on Tuesday at 3 PM.",
        height=160,
        label_visibility="collapsed",
    )

    if st.button("💾 Save Memory", use_container_width=True, type="primary"):
        if not text.strip():
            st.error("Please enter some text before saving.")
        elif len(text) > MAX_TEXT_LENGTH:
            st.warning(
                f"Text is too long ({len(text):,} chars). "
                f"Please keep it under {MAX_TEXT_LENGTH:,} characters."
            )
        else:
            with st.spinner("Embedding and saving…"):
                records = create_memories_from_text(text, embedder)
                ids = save_memories(records)

            chunks_label = "chunk" if len(ids) == 1 else "chunks"
            st.success(
                f"Saved **{len(ids)} {chunks_label}** "
                f"(ID{'s' if len(ids) > 1 else ''}: {', '.join(str(i) for i in ids)})"
            )
            preview = text[:120] + ("..." if len(text) > 120 else "")
            st.markdown(f'> *Stored:* "{preview}"')
            # Sidebar count refreshes on next rerun
            st.rerun()


# ── Page 2: Ask Question ─────────────────────────────────────────────────────

elif page == "❓ Ask Question":
    st.header("Ask About Your Memories")
    st.caption(
        "Ask anything you've stored. "
        "The app retrieves the most relevant memories, then generates a grounded answer on-device."
    )

    question = st.text_input(
        "Your question",
        placeholder="e.g. When is my dentist appointment?",
        label_visibility="collapsed",
    )

    if st.button("🔍 Ask", use_container_width=True, type="primary"):
        if not question.strip():
            st.error("Please type a question first.")
        elif count_memories() == 0:
            st.warning(
                "No memories stored yet. Switch to **📝 Add Memory** and add some first.",
                icon="⚠️",
            )
        else:
            t_search_start = time.perf_counter()
            with st.spinner("Searching memories…"):
                results = search_memories(question, embedder)
            retrieval_latency = time.perf_counter() - t_search_start

            # Attempt LLM generation with graceful error handling
            answer = None
            gen_latency = 0.0
            if not model_ok:
                st.warning(
                    "LLM model not available — showing retrieved memories only. "
                    "Run `task pull-model` to enable answer generation.",
                    icon="⚠️",
                )
            else:
                try:
                    with st.spinner("Generating answer (this may take 10-30s on first run)…"):
                        t_gen_start = time.perf_counter()
                        answer = generate_answer(question, [r[0] for r in results])
                        gen_latency = time.perf_counter() - t_gen_start
                except FileNotFoundError:
                    st.error(
                        "❌ **Model file not found.** Run `task pull-model` to download it, "
                        "then refresh this page."
                    )
                except RuntimeError as e:
                    st.error(f"❌ **Generation error:** {e}")
                except Exception as e:
                    st.error(f"❌ **Unexpected error:** {e}")

            # ── Answer ──
            if answer:
                st.subheader("💡 Answer")
                st.info(answer, icon="💡")

                # Latency & Pipeline metrics
                total_latency = retrieval_latency + gen_latency
                col1, col2, col3 = st.columns(3)
                col1.metric("⏱️ Total Latency", f"{total_latency:.2f}s")
                col2.metric("🔍 Retrieval Time", f"{retrieval_latency * 1000:.0f} ms")
                col3.metric("🧠 LLM Generation", f"{gen_latency:.2f}s")

                pipeline_parts = []
                if settings.EXPAND_QUERY:
                    pipeline_parts.append("✨ Query Expansion")
                if settings.POOL_K > settings.TOP_K:
                    pipeline_parts.append(f"🏊 Widen Pool (k={settings.POOL_K})")
                if settings.RERANK:
                    pipeline_parts.append("🎯 Cross-Encoder Rerank")
                if not pipeline_parts:
                    pipeline_parts.append("📦 Baseline Hybrid")

                st.caption(f"**Pipeline Active:** {' · '.join(pipeline_parts)}")

            st.divider()

            # ── Retrieved context ──
            if results:
                st.subheader(f"📚 Retrieved Memories ({len(results)} found)")
                # Fetch BM25 matches directly from FTS5 for this query
                sparse_map = {r.id: s for r, s in _sparse_search(question) if r.id is not None}

                for i, hit in enumerate(results, 1):
                    rec = hit.record if hasattr(hit, "record") else hit[0]
                    score = hit.score if hasattr(hit, "score") else hit[1]
                    sem_score = getattr(hit, "semantic_score", None)
                    bm25_score = getattr(hit, "bm25_score", None)
                    match_type = getattr(hit, "match_type", None)

                    # Ensure semantic score is always present
                    if sem_score is None and getattr(rec, "embedding", None):
                        try:
                            q_vec = embedder.embed(question)
                            sem_score = float(np.dot(rec.embedding, q_vec))
                        except Exception:
                            sem_score = 0.0

                    # Ensure BM25 score is populated if it matched in FTS5
                    if (bm25_score is None or bm25_score == 0.0) and rec.id in sparse_map:
                        bm25_score = sparse_map[rec.id]

                    has_sem = sem_score is not None and sem_score > 0.3
                    has_bm = bm25_score is not None and bm25_score > 0.0

                    if match_type == "both" or (has_sem and has_bm):
                        badge = "⚡ Both (Semantic + BM25)"
                    elif match_type == "bm25" or has_bm:
                        badge = "🔤 BM25 Keyword"
                    else:
                        badge = "🧠 Semantic"

                    sem_str = f"{sem_score:.4f}" if sem_score is not None else "0.0000"
                    bm25_str = f"{bm25_score:.4f}" if bm25_score is not None else "0.0000"

                    preview = rec.text[:65] + ("..." if len(rec.text) > 65 else "")
                    title = f"{i}. [{badge}] · Fused {score:.4f} · {preview}"

                    with st.expander(title, expanded=(i == 1)):
                        st.markdown(f"**Text:** {rec.text}")
                        st.markdown(
                            f"<small style='opacity: 0.9;'>"
                            f"📊 <b>Semantic Cosine:</b> <code>{sem_str}</code> &nbsp;|&nbsp; "
                            f"<b>BM25:</b> <code>{bm25_str}</code> &nbsp;|&nbsp; "
                            f"<b>Fused RRF:</b> <code>{score:.4f}</code> &nbsp;|&nbsp; "
                            f"🕒 {rec.timestamp.strftime('%d %b %Y, %H:%M')}"
                            f"</small>",
                            unsafe_allow_html=True,
                        )
                        st.caption(
                            f"Source: {rec.source_type} · "
                            f"Chunk {rec.metadata.get('chunk_index', 0) + 1} of "
                            f"{rec.metadata.get('total_chunks', 1)} · "
                            f"{rec.metadata.get('token_count', '?')} tokens"
                        )
            else:
                st.info("No relevant memories found.", icon="🔎")
