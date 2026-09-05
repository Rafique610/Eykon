"""RAG Retrieval Benchmark — Persistent Memory App.

Usage:
    uv run python src/benchmarks/run.py

Uses a completely separate benchmark database (data/benchmark.db) so it never
touches the real app memories. The database is cleared and repopulated fresh
on every run to ensure reproducible results.

Output:
    - Formatted table printed to stdout
    - Full per-query results saved to data/benchmark_results.json
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.benchmarks.data import CORPUS_MEMORIES, GOLD_MEMORIES, QA_PAIRS
from src.benchmarks.metrics import (
    aggregate,
    hit_at_k,
    ndcg_at_k,
    precision_at_k,
    reciprocal_rank,
)
from src.memories.database import init_db
from src.memories.embedder import Embedder
from src.memories.repository import clear_all_memories, count_memories, save_memories
from src.memories.search import search_memories
from src.memories.service import create_memories_from_text

BENCHMARK_DB = ROOT / "data" / "benchmark.db"
TOP_K = 5
MODES = ["hybrid", "semantic", "keyword"]
MODE_LABELS = {"hybrid": "Hybrid (Dense+BM25)", "semantic": "Semantic", "keyword": "Keyword (BM25)"}


# ── Database setup ────────────────────────────────────────────────────────────

def _setup_db() -> None:
    init_db(db_path=BENCHMARK_DB)
    cleared = clear_all_memories(db_path=BENCHMARK_DB)
    if cleared:
        print(f"  Cleared {cleared} existing benchmark chunks.")


# ── Memory insertion ──────────────────────────────────────────────────────────

def _insert_all(embedder: Embedder) -> dict[str, list[int]]:
    """Insert gold + corpus memories. Return {gold_key: [chunk_ids]} for QA lookup."""
    key_to_ids: dict[str, list[int]] = {}
    total_gold = len(GOLD_MEMORIES)
    total_corpus = len(CORPUS_MEMORIES)

    print(f"  Inserting {total_gold} gold memories...")
    for i, (key, text) in enumerate(GOLD_MEMORIES, 1):
        records = create_memories_from_text(text, embedder)
        for r in records:
            r.metadata["benchmark_key"] = key        # tag for lookup later
        ids = save_memories(records, db_path=BENCHMARK_DB)
        key_to_ids[key] = ids
        if i % 10 == 0 or i == total_gold:
            print(f"    Gold {i}/{total_gold}", end="\r")

    print(f"\n  Inserting {total_corpus} corpus memories (noise)...")
    batch_size = 50
    for start in range(0, total_corpus, batch_size):
        batch = CORPUS_MEMORIES[start : start + batch_size]
        for text in batch:
            records = create_memories_from_text(text, embedder)
            save_memories(records, db_path=BENCHMARK_DB)
        done = min(start + batch_size, total_corpus)
        print(f"    Corpus {done}/{total_corpus}", end="\r")

    print()
    return key_to_ids


# ── Benchmark run ─────────────────────────────────────────────────────────────

def _run_all_modes(
    embedder: Embedder,
    key_to_ids: dict[str, list[int]],
    expand: bool = False,
    pool_k: int | None = None,
    rerank: bool = False,
) -> dict[str, list[dict]]:
    """Run every QA pair in every mode. Returns {mode: [per_query_results]}."""
    results: dict[str, list[dict]] = {}

    for mode in MODES:
        mode_results: list[dict] = []
        for qa in QA_PAIRS:
            gold_ids: set[int] = set()
            for key in qa["gold_keys"]:
                gold_ids.update(key_to_ids.get(key, []))

            if not gold_ids:
                # Gold memory was not found in DB — skip with warning
                print(f"  WARN: No chunks found for gold keys {qa['gold_keys']}")
                continue

            t0 = time.time()
            hits = search_memories(
                qa["question"], embedder, top_k=TOP_K, mode=mode,
                db_path=BENCHMARK_DB, expand=expand, pool_k=pool_k, rerank=rerank,
            )
            latency_ms = (time.time() - t0) * 1000
            retrieved_ids = [h[0].id for h in hits if h[0].id is not None]

            mode_results.append({
                "id": qa["id"],
                "query_type": qa["query_type"],
                "question": qa["question"],
                "gold_keys": qa["gold_keys"],
                "gold_ids": sorted(gold_ids),
                "retrieved_ids": retrieved_ids,
                "hit@1":   hit_at_k(retrieved_ids, gold_ids, 1),
                "hit@3":   hit_at_k(retrieved_ids, gold_ids, 3),
                "hit@5":   hit_at_k(retrieved_ids, gold_ids, 5),
                "mrr":     reciprocal_rank(retrieved_ids, gold_ids),
                "p@5":     precision_at_k(retrieved_ids, gold_ids, 5),
                "ndcg@5":  ndcg_at_k(retrieved_ids, gold_ids, 5),
                "latency_ms": latency_ms,
            })

        results[mode] = mode_results

    return results


# ── Display ───────────────────────────────────────────────────────────────────

def _fmt(v: float) -> str:
    return f"{v:.4f}"


def _print_overall_table(mode_aggs: dict[str, dict]) -> None:
    w = 20
    print()
    print("  Overall Results (all 30 queries)")
    print("  " + "─" * 94)
    print(f"  {'Mode':<{w}}  {'Hit@1':>6}  {'Hit@3':>6}  {'Hit@5':>6}  {'MRR':>6}  {'P@5':>6}  {'NDCG@5':>7}  {'Latency':>8}")
    print("  " + "─" * 94)
    for mode in MODES:
        agg = mode_aggs.get(mode, {})
        label = MODE_LABELS[mode]
        lat = agg.get('latency_ms', 0)
        print(
            f"  {label:<{w}}  "
            f"{_fmt(agg.get('hit@1', 0)):>6}  "
            f"{_fmt(agg.get('hit@3', 0)):>6}  "
            f"{_fmt(agg.get('hit@5', 0)):>6}  "
            f"{_fmt(agg.get('mrr', 0)):>6}  "
            f"{_fmt(agg.get('p@5', 0)):>6}  "
            f"{_fmt(agg.get('ndcg@5', 0)):>7}  "
            f"{lat:>6.1f}ms"
        )
    print("  " + "─" * 94)


def _print_per_type_table(hybrid_results: list[dict]) -> None:
    query_types = ["exact", "semantic", "multi_hop"]
    type_labels = {"exact": "Exact recall (10)", "semantic": "Semantic (10)", "multi_hop": "Multi-hop (10)"}
    w = 20
    print()
    print("  Per Query Type — Hybrid mode")
    print("  " + "─" * 66)
    print(f"  {'Type':<{w}}  {'Hit@1':>6}  {'Hit@3':>6}  {'Hit@5':>6}  {'MRR':>6}  {'Latency':>8}")
    print("  " + "─" * 66)
    for qt in query_types:
        agg = aggregate([r for r in hybrid_results if r["query_type"] == qt])
        label = type_labels.get(qt, qt)
        lat = agg.get('latency_ms', 0)
        print(
            f"  {label:<{w}}  "
            f"{_fmt(agg.get('hit@1', 0)):>6}  "
            f"{_fmt(agg.get('hit@3', 0)):>6}  "
            f"{_fmt(agg.get('hit@5', 0)):>6}  "
            f"{_fmt(agg.get('mrr', 0)):>6}  "
            f"{lat:>6.1f}ms"
        )
    print("  " + "─" * 66)


def _print_per_query_detail(hybrid_results: list[dict]) -> None:
    print()
    print("  Per-Query Detail — Hybrid mode")
    print("  " + "─" * 98)
    print(f"  {'#':>3}  {'Type':<10}  {'Hit@1':>5}  {'Hit@3':>5}  {'Hit@5':>5}  {'MRR':>6}  {'Latency':>8}  Question")
    print("  " + "─" * 98)
    for r in hybrid_results:
        q_short = r["question"][:50] + ("…" if len(r["question"]) > 50 else "")
        hit1 = "Y" if r["hit@1"] else "."
        hit3 = "Y" if r["hit@3"] else "."
        hit5 = "Y" if r["hit@5"] else "."
        lat = r.get('latency_ms', 0)
        print(
            f"  {r['id']:>3}  {r['query_type']:<10}  "
            f"{hit1:>5}  {hit3:>5}  {hit5:>5}  "
            f"{_fmt(r['mrr']):>6}  {lat:>6.1f}ms  {q_short}"
        )
    print("  " + "─" * 98)


# ── Main ──────────────────────────────────────────────────────────────────────

import argparse

def main() -> None:
    parser = argparse.ArgumentParser(description="Run RAG retrieval benchmark.")
    parser.add_argument("--expand", action="store_true", help="Enable query expansion")
    parser.add_argument("--pool-k", type=int, default=None, help="Pool size for hybrid search")
    parser.add_argument("--rerank", action="store_true", help="Enable cross-encoder re-ranking")
    args, _ = parser.parse_known_args()

    t_start = time.time()

    print()
    print("══════════════════════════════════════════════════════════")
    title = "   RAG Retrieval Benchmark"
    extras = []
    if args.expand:
        extras.append("Expanded")
    if args.pool_k is not None:
        extras.append(f"Pool={args.pool_k}")
    if args.rerank:
        extras.append("Re-ranked")
    
    if extras:
        title += f" ({', '.join(extras)})"
        
    print(f"{title:<58}")
    print("══════════════════════════════════════════════════════════")
    print()

    # 1. Load embedder
    print("[1/4] Loading embedder...")
    embedder = Embedder()
    print("  OK")

    # 2. Setup DB
    print("[2/4] Setting up benchmark database...")
    _setup_db()
    print("  OK")

    # 3. Insert memories
    print("[3/4] Inserting memories...")
    t_insert = time.time()
    key_to_ids = _insert_all(embedder)
    total_chunks = count_memories(db_path=BENCHMARK_DB)
    elapsed_insert = time.time() - t_insert
    gold_chunks = sum(len(v) for v in key_to_ids.values())
    print(
        f"  Inserted {len(GOLD_MEMORIES)} gold ({gold_chunks} chunks) + "
        f"{len(CORPUS_MEMORIES)} corpus → {total_chunks} total chunks "
        f"in {elapsed_insert:.1f}s"
    )

    # 4. Run benchmark
    print(f"[4/4] Running {len(QA_PAIRS)} queries × {len(MODES)} modes...")
    t_bench = time.time()
    mode_results = _run_all_modes(embedder, key_to_ids, expand=args.expand, pool_k=args.pool_k, rerank=args.rerank)
    elapsed_bench = time.time() - t_bench
    print(f"  Completed in {elapsed_bench:.1f}s")

    # ── Print results ──────────────────────────────────────────────────────
    print()
    print("══════════════════════════════════════════════════════════")
    print(
        f"  {len(GOLD_MEMORIES) + len(CORPUS_MEMORIES)} memories → "
        f"{total_chunks} chunks  |  "
        f"{len(QA_PAIRS)} queries  |  top_k = {TOP_K}"
    )
    print("══════════════════════════════════════════════════════════")

    mode_aggs = {mode: aggregate(results) for mode, results in mode_results.items()}
    _print_overall_table(mode_aggs)

    if "hybrid" in mode_results:
        _print_per_type_table(mode_results["hybrid"])
        _print_per_query_detail(mode_results["hybrid"])

    # ── Save JSON ─────────────────────────────────────────────────────────
    out = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "total_memories": len(GOLD_MEMORIES) + len(CORPUS_MEMORIES),
            "total_chunks": total_chunks,
            "gold_memories": len(GOLD_MEMORIES),
            "corpus_memories": len(CORPUS_MEMORIES),
            "top_k": TOP_K,
            "n_queries": len(QA_PAIRS),
        },
        "overall": mode_aggs,
        "per_query_type": {
            mode: {
                qt: aggregate([r for r in results if r["query_type"] == qt])
                for qt in ["exact", "semantic", "multi_hop"]
            }
            for mode, results in mode_results.items()
        },
        "per_query": mode_results,
    }

    out_path = ROOT / "data" / "benchmark_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))

    elapsed_total = time.time() - t_start
    print()
    print(f"  Results saved → {out_path.relative_to(ROOT)}")
    print(f"  Total runtime: {elapsed_total:.1f}s")
    print()
    print("══════════════════════════════════════════════════════════")
    print()


if __name__ == "__main__":
    main()
