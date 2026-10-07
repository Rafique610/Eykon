"""Experiments A5 & A6: Cross-pipeline quality and shared model test.

Usage:
    uv run python src/benchmarks/cross_pipeline.py --experiment a5 --videos data/a5_video_*.mp4
    uv run python src/benchmarks/cross_pipeline.py --experiment a6 --videos data/a5_video_*.mp4
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from src.benchmarks._captioners import A6_MODELS, caption_with_gemma4, caption_with_llama
from src.benchmarks.data import CORPUS_MEMORIES, GOLD_MEMORIES, QA_PAIRS
from src.benchmarks.metrics import aggregate, hit_at_k, reciprocal_rank
from src.memories.database import init_db
from src.memories.embedder import Embedder
from src.memories.models import MemoryRecord
from src.memories.repository import clear_all_memories, save_memories
from src.memories.search import search_memories
from src.memories.service import create_memories_from_text
from src.vision.extractor import extract_frames

A5_DB = ROOT / "data" / "benchmark_a5.db"
A6_DB = ROOT / "data" / "benchmark_a6.db"
TOP_K = 5

# QA pairs for the 5 new object-location videos (a5_video_1 … a5_video_5).
# Keywords drive the keyword-hit metric; query goes to retrieval + Gemma 4 generation.
VIDEO_QA_PAIRS = [
    {"query": "Where did I leave my keys?",       "keywords": ["key", "keys", "hook", "kitchen", "table", "door"]},
    {"query": "Where did I hang my keys?",         "keywords": ["hook", "door", "hung", "hanging", "key"]},
    {"query": "Where is my wallet?",               "keywords": ["wallet", "bedside", "bedroom", "table", "phone"]},
    {"query": "Where did I put my wallet?",        "keywords": ["wallet", "bedside", "table", "bedroom"]},
    {"query": "Where are my earbuds?",             "keywords": ["earbud", "earbuds", "drawer", "desk", "case", "white"]},
    {"query": "Where did I put my earbuds case?",  "keywords": ["drawer", "desk", "case", "earbud"]},
    {"query": "Where is my umbrella?",             "keywords": ["umbrella", "hook", "door", "wall", "blue"]},
    {"query": "Where did I hang my umbrella?",     "keywords": ["hook", "door", "umbrella", "hang", "hung"]},
    {"query": "Where is my watch?",                "keywords": ["watch", "bathroom", "counter", "sink", "brown"]},
    {"query": "Where did I put my watch?",         "keywords": ["bathroom", "counter", "toothbrush", "watch"]},
]


# ── Shared retrieval helpers ──────────────────────────────────────────────────

def _text_memories_into(db_path: Path, embedder: Embedder) -> dict[str, list[int]]:
    """Fresh DB with Phase 1 gold + corpus. Returns key→chunk_ids for regression test."""
    init_db(db_path=db_path)
    cleared = clear_all_memories(db_path=db_path)
    if cleared:
        print(f"  Cleared {cleared} existing chunks.")
    key_to_ids: dict[str, list[int]] = {}
    for key, text in GOLD_MEMORIES:
        records = create_memories_from_text(text, embedder)
        key_to_ids[key] = save_memories(records, db_path=db_path)
    for text in CORPUS_MEMORIES:
        save_memories(create_memories_from_text(text, embedder), db_path=db_path)
    return key_to_ids


def _run_regression(embedder: Embedder, key_to_ids: dict[str, list[int]], db_path: Path) -> list[dict]:
    """Phase 1 gold-ID regression: 30 QA pairs, hybrid+rerank, returns per-query dicts."""
    results = []
    for qa in QA_PAIRS:
        gold_ids: set[int] = set()
        for k in qa["gold_keys"]:
            gold_ids.update(key_to_ids.get(k, []))
        t0 = time.time()
        hits = search_memories(qa["question"], embedder, top_k=TOP_K, mode="hybrid",
                               db_path=db_path, expand=True, pool_k=20, rerank=True)
        lat = (time.time() - t0) * 1000
        ids = [h[0].id for h in hits if h[0].id is not None]
        results.append({
            "id": qa["id"], "question": qa["question"], "gold_keys": qa["gold_keys"],
            "hit@1": hit_at_k(ids, gold_ids, 1), "hit@5": hit_at_k(ids, gold_ids, 5),
            "mrr": reciprocal_rank(ids, gold_ids), "latency_ms": lat,
            "top_chunks": [h[0].text for h in hits[:3]],
        })
    return results


def _run_video_qa(embedder: Embedder, db_path: Path) -> list[dict]:
    """Keyword-hit retrieval on VIDEO_QA_PAIRS. Gold IDs not available for video content."""
    results = []
    for qa in VIDEO_QA_PAIRS:
        t0 = time.time()
        hits = search_memories(qa["query"], embedder, top_k=TOP_K, mode="hybrid",
                               db_path=db_path, expand=True, pool_k=20, rerank=True)
        lat = (time.time() - t0) * 1000
        texts = [h[0].text.lower() for h in hits]
        rank = next((i + 1 for i, t in enumerate(texts)
                     if any(k in t for k in qa["keywords"])), None)
        results.append({
            "query": qa["query"], "keywords": qa["keywords"],
            "hit@1": 1.0 if rank == 1 else 0.0,
            "hit@5": 1.0 if rank is not None else 0.0,
            "mrr": (1.0 / rank) if rank else 0.0,
            "latency_ms": lat,
            "top_chunks": [h[0].text for h in hits[:3]],
        })
    return results


def _attach_generated_answers(results: list[dict], query_key: str = "question") -> list[dict]:
    """Run Gemma 4 E2B on each result's top_chunks and attach generated_answer.
    Stored for Step 12 LLM-as-judge. Prints each Q/A pair as it goes."""
    from src.assistant.llm import generate_answer, get_engine
    try:
        engine = get_engine()
    except FileNotFoundError:
        print("  [WARN] Gemma 4 not found — answers skipped. Run 'task pull-model'.")
        for r in results:
            r["generated_answer"] = "SKIPPED: model not downloaded"
        return results
    for r in results:
        q = r.get(query_key) or r.get("query") or r.get("question", "")
        chunks = [MemoryRecord(text=t, source="benchmark") for t in r["top_chunks"]]
        try:
            r["generated_answer"] = generate_answer(q, chunks, engine=engine)
        except Exception as e:
            r["generated_answer"] = f"ERROR: {e}"
        print(f"  Q: {q[:60]}")
        print(f"  A: {r['generated_answer'][:110]}\n")
    return results


def _delta_row(label: str, b: float, v: float) -> str:
    d = v - b
    return f"│ {label:<11} │ {b:>19.4f} │ {v:>19.4f} │ {d:>+8.4f} │"


# ── Experiment A5 ─────────────────────────────────────────────────────────────

def run_a5(video_paths: list[str]) -> None:
    print("\n══════════ A5: Cross-Pipeline Retrieval Quality ══════════")
    embedder = Embedder()

    print("\n[1/5] Building Phase 1 DB (text-only baseline)...")
    key_to_ids = _text_memories_into(A5_DB, embedder)

    print("[2/5] Regression baseline — 30 Phase 1 QA pairs...")
    base = _run_regression(embedder, key_to_ids, A5_DB)
    base_agg = aggregate(base)
    print(f"  Hit@1={base_agg['hit@1']:.4f}  Hit@5={base_agg['hit@5']:.4f}  MRR={base_agg['mrr']:.4f}")

    # Add video memories using the configured SmolVLM (same as the production pipeline)
    print(f"\n[3/5] Captioning {len(video_paths)} video(s) with SmolVLM (production VLM)...")
    from src.vision import process_video
    total_added = 0
    for vp in video_paths:
        if not Path(vp).exists():
            print(f"  [SKIP] {vp}"); continue
        from src.memories.service import create_memories_from_video
        frames = process_video(vp, interval_seconds=1.0)
        records = create_memories_from_video(frames, Path(vp).name, embedder)
        save_memories(records, db_path=A5_DB)
        total_added += len(records)
        print(f"  {Path(vp).name}: {len(frames)} frames → {len(records)} memories")
    print(f"  Total video memories added: {total_added}")

    print("\n[4/5] Re-running Phase 1 regression (text + video mixed DB)...")
    after = _run_regression(embedder, key_to_ids, A5_DB)
    after_agg = aggregate(after)

    print("\n  ── Regression Delta (Phase 1 text QA pairs) ───────────────────────")
    print("┌─────────────┬─────────────────────┬─────────────────────┬──────────┐")
    print("│ Metric      │ Baseline (text)     │ With Video Memories │  Delta   │")
    print("├─────────────┼─────────────────────┼─────────────────────┼──────────┤")
    for k, lbl in [("hit@1","Hit@1"),("hit@5","Hit@5"),("mrr","MRR"),("latency_ms","Latency ms")]:
        print(_delta_row(lbl, base_agg.get(k,0), after_agg.get(k,0)))
    print("└─────────────┴─────────────────────┴─────────────────────┴──────────┘")

    print("\n[5/5] Running video-specific QA + generating Gemma 4 answers (for Step 12)...")
    video_qa = _run_video_qa(embedder, A5_DB)
    vq_agg = aggregate(video_qa)
    print(f"\n  Video QA → Hit@1={vq_agg['hit@1']:.4f}  Hit@5={vq_agg['hit@5']:.4f}  MRR={vq_agg['mrr']:.4f}")
    print("\n  Generating answers:\n")
    video_qa = _attach_generated_answers(video_qa, query_key="query")

    out = ROOT / "data" / "experiment_a5_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "regression": {"baseline": base_agg, "with_video": after_agg,
                       "video_memories_added": total_added, "per_query": after},
        "video_qa": {"metrics": vq_agg, "per_query": video_qa},
    }, indent=2, ensure_ascii=False))
    print(f"  ✓ Saved → {out.relative_to(ROOT)}\n")


# ── Experiment A6 ─────────────────────────────────────────────────────────────

def run_a6(video_paths: list[str], n_frames: int = 20) -> None:
    print("\n══════════ A6: 3-VLM End-to-End Comparison ═══════════════")
    embedder = Embedder()
    table_rows: list[dict] = []

    for cfg in A6_MODELS:
        label = cfg["label"]
        print(f"\n── [{label}] ──────────────────────────────────────────")

        # Fresh video-only DB for each VLM (no text memories — isolates caption quality)
        init_db(db_path=A6_DB)
        clear_all_memories(db_path=A6_DB)

        all_captions: list[str] = []
        all_lats: list[float] = []
        total_ram = 0.0

        for vp in video_paths:
            if not Path(vp).exists():
                print(f"  [SKIP] {vp}"); continue
            frames = extract_frames(vp, interval_seconds=1.0)[:n_frames]
            try:
                if cfg["type"] == "llama":
                    caps, lats, ram = caption_with_llama(cfg, frames, len(frames))
                else:
                    caps, lats, ram = caption_with_gemma4(cfg.get("model"), frames, len(frames))
            except Exception as e:
                print(f"  FAILED on {Path(vp).name}: {e}"); continue

            # Store captions as memories
            for cap, frame in zip(caps, frames):
                if cap.startswith("SKIPPED"):
                    continue
                rec = MemoryRecord(
                    text=cap, source="video",
                    metadata={"video": Path(vp).name,
                               "timestamp": round(frame.timestamp_seconds, 1)},
                )
                rec.embedding = embedder.embed(cap)
                save_memories([rec], db_path=A6_DB)

            all_captions.extend(caps)
            all_lats.extend(lats)
            total_ram = max(total_ram, ram)  # peak across videos
            print(f"  {Path(vp).name}: {len(frames)} frames captioned")

        if not all_lats:
            table_rows.append({"model": label, "status": "NO OUTPUT"}); continue

        avg_lat = float(np.mean(all_lats))
        print(f"  Avg latency: {avg_lat:.1f}s  RAM: {round(total_ram)}MB")

        print("  Running video QA retrieval...")
        vq_results = _run_video_qa(embedder, A6_DB)
        vq_agg = aggregate(vq_results)
        print(f"  Hit@1={vq_agg['hit@1']:.4f}  Hit@5={vq_agg['hit@5']:.4f}  MRR={vq_agg['mrr']:.4f}")

        print("  Generating Gemma 4 answers (stored for Step 12 judge)...\n")
        vq_results = _attach_generated_answers(vq_results, query_key="query")

        table_rows.append({
            "model": label,
            "ram_mb": round(total_ram),
            "avg_latency_s": round(avg_lat, 1),
            "hit@1": vq_agg["hit@1"], "hit@5": vq_agg["hit@5"], "mrr": vq_agg["mrr"],
            "per_query": vq_results,
            "status": "OK",
        })

    # Comparison table
    print("\n┌──────────────────────────┬──────────┬─────────────┬───────┬───────┬────────┐")
    print("│ Model                    │ RAM (MB) │ Latency (s) │ Hit@1 │ Hit@5 │ MRR    │")
    print("├──────────────────────────┼──────────┼─────────────┼───────┼───────┼────────┤")
    for r in table_rows:
        if r.get("status") != "OK":
            print(f"│ {r['model']:<24} │ {'—':>8} │ {'—':>11} │ {'—':>5} │ {'—':>5} │ {'—':>6} │")
        else:
            print(f"│ {r['model']:<24} │ {r['ram_mb']:>8} │ {r['avg_latency_s']:>11.1f} │"
                  f" {r['hit@1']:>5.4f} │ {r['hit@5']:>5.4f} │ {r['mrr']:>6.4f} │")
    print("└──────────────────────────┴──────────┴─────────────┴───────┴───────┴────────┘")

    out = ROOT / "data" / "experiment_a6_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"models": table_rows}, indent=2, ensure_ascii=False))
    print(f"\n  ✓ Saved → {out.relative_to(ROOT)}\n")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Experiments A5 & A6.")
    parser.add_argument("--experiment", choices=["a5", "a6"], required=True)
    parser.add_argument("--videos", nargs="+", default=[], help="Video files (both A5 and A6)")
    parser.add_argument("--frames", type=int, default=20, help="Max frames per video for A6")
    args = parser.parse_args()

    if not args.videos:
        parser.error("--videos is required")

    if args.experiment == "a5":
        run_a5(args.videos)
    else:
        run_a6(args.videos, args.frames)
