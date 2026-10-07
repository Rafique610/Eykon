import argparse
import time
import json
import os
import numpy as np
from pathlib import Path
import sys

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.vision import process_video
from src.memories import Embedder, init_db, save_memories, search_memories, clear_all_memories
from src.memories.service import create_memories_from_video

# Default videos for experiments (all three generated test videos).
DEFAULT_VIDEOS = [
    "data/video1.mp4",
    "data/video2.mp4",
    "data/video3.mp4",
]

# Ground-truth QA pairs based on exact visual content of each video.
#
# video1 — Kitchen counter scene:
#   Objects visible: red mug, sunglasses (picked up from counter, then placed back),
#   cereal box (Froot Loops, orange), bread loaf in bag, bag of pretzels, spoons,
#   bread crumbs on counter. Fridge and sink in background.
#
# video2 — Bedroom scene:
#   Objects visible: red passport (found on cluttered floor with clothes/shoes,
#   placed on grey unmade bed, then held alongside white over-ear headphones,
#   then packed into black backpack). Nightstand with small plant in background.
#
# video3 — Home office / desk scene (evening, lamp on):
#   Objects visible: closed silver laptop with a yellow sticky note (smiley face drawn)
#   on its lid, blue ballpoint pen on desk, scattered white papers/documents,
#   blue water bottle (placed on desk mid-video), metal desk lamp, pen holder with pens.
VIDEO_QA_PAIRS: dict[str, list[dict]] = {
    "video1.mp4": [
        {
            "query": "Where did I put my sunglasses?",
            "keywords": ["sunglasses", "counter", "kitchen", "counter top", "glasses"],
        },
        {
            "query": "What is the red mug doing on the counter?",
            "keywords": ["red", "mug", "cup", "counter", "kitchen"],
        },
        {
            "query": "What food or snack items are on the kitchen counter?",
            "keywords": ["pretzel", "bread", "cereal", "froot loops", "snack", "loaf", "bag"],
        },
    ],
    "video2.mp4": [
        {
            "query": "Where did I leave my passport?",
            "keywords": ["passport", "red", "bed", "floor", "bedroom", "document"],
        },
        {
            "query": "Where did I find my passport?",
            "keywords": ["floor", "clothes", "bedroom", "ground", "pile"],
        },
        {
            "query": "Where did I pack my passport?",
            "keywords": ["backpack", "bag", "packed", "black", "inserted"],
        },
    ],
    "video3.mp4": [
        {
            "query": "What is on the laptop lid?",
            "keywords": ["sticky", "note", "yellow", "smiley", "sticker", "post-it"],
        },
        {
            "query": "What is placed on the desk next to the laptop?",
            "keywords": ["water", "bottle", "blue", "papers", "documents", "pen"],
        },
        {
            "query": "What papers or documents are on the desk?",
            "keywords": ["papers", "documents", "sheets", "scattered", "printed", "white"],
        },
    ],
}


def calculate_metrics(results, qa_pairs):
    mrr_sum = 0
    hits_at_1 = 0
    hits_at_3 = 0
    hits_at_5 = 0
    precision_at_3_sum = 0
    recall_at_3_sum = 0 # Assuming 1 relevant chunk per query
    
    for i, res_list in enumerate(results):
        keywords = qa_pairs[i]["keywords"]
        
        hit_rank = None
        relevant_count_in_top_3 = 0
        for rank, r in enumerate(res_list):
            text = r.record.text.lower() if hasattr(r, 'record') else r[0].text.lower()
            if any(k in text for k in keywords):
                if hit_rank is None:
                    hit_rank = rank + 1
                if rank < 3:
                    relevant_count_in_top_3 += 1
                    
        if hit_rank is not None:
            mrr_sum += 1.0 / hit_rank
            if hit_rank == 1: hits_at_1 += 1
            if hit_rank <= 3: hits_at_3 += 1
            if hit_rank <= 5: hits_at_5 += 1
            
        precision_at_3_sum += relevant_count_in_top_3 / 3.0
        recall_at_3_sum += 1 if relevant_count_in_top_3 > 0 else 0
        
    n = len(qa_pairs)
    return {
        "MRR": mrr_sum / n,
        "Hit@1": hits_at_1 / n,
        "Hit@3": hits_at_3 / n,
        "Hit@5": hits_at_5 / n,
        "Precision@3": precision_at_3_sum / n,
        "Recall@3": recall_at_3_sum / n
    }

from src.benchmarks.experiment_a1 import run_experiment_a1  # noqa: F401  (A1 lives in its own file)

def run_experiment_a2(video_path: str, embedder: Embedder, qa_pairs: list[dict]):
    print("\n--- Experiment A2: Frame Sampling Rate vs Accuracy ---")
    intervals = [10.0, 5.0, 3.0, 1.0]  # fastest → densest
    results_table = []

    for interval in intervals:
        print(f"\n[Testing {interval}s interval]")
        init_db()
        clear_all_memories()

        t0 = time.perf_counter()
        frames = process_video(video_path, interval_seconds=interval)
        process_time = time.perf_counter() - t0

        if frames:
            records = create_memories_from_video(frames, Path(video_path).name, embedder)
            save_memories(records)

            search_results = [search_memories(qa["query"], embedder, top_k=5) for qa in qa_pairs]
            metrics = calculate_metrics(search_results, qa_pairs)

            results_table.append({
                "Interval": f"{interval}s",
                "Frames": len(frames),
                "Time (s)": round(process_time, 1),
                "Hit@3": metrics["Hit@3"],
                "Hit@5": metrics["Hit@5"],
                "Precision@3": metrics["Precision@3"],
                "Recall@3": metrics["Recall@3"],
                "MRR": metrics["MRR"],
            })
        else:
            print("  No frames extracted at this interval.")

    print("\n| Interval | Frames | Time(s) | Hit@3 | Precision@3 | Recall@3 | MRR |")
    print("|---|---|---|---|---|---|---|")
    for r in results_table:
        print(f"| {r['Interval']} | {r['Frames']} | {r['Time (s)']} | {r['Hit@3']:.2f} | {r['Precision@3']:.2f} | {r['Recall@3']:.2f} | {r['MRR']:.2f} |")

    return results_table


def run_experiment_a3(video_path: str, embedder: Embedder, qa_pairs: list[dict]):
    print("\n--- Experiment A3: Caption Style vs Accuracy ---")

    prompts = {
        "Short": "Describe what you see in this image in one detailed sentence.",
        "Long": "Describe everything you see in detail, including objects, colors, positions, and any text visible.",
    }

    results_table = []

    for style, prompt in prompts.items():
        print(f"\n[Testing {style} prompt]")
        init_db()
        clear_all_memories()

        t0 = time.perf_counter()
        frames = process_video(video_path, interval_seconds=3.0, caption_prompt=prompt)
        process_time = time.perf_counter() - t0

        if frames:
            avg_tokens = np.mean([len(f.caption.split()) for f in frames])
            records = create_memories_from_video(frames, Path(video_path).name, embedder)
            save_memories(records)

            search_results = [search_memories(qa["query"], embedder, top_k=5) for qa in qa_pairs]
            metrics = calculate_metrics(search_results, qa_pairs)

            results_table.append({
                "Style": style,
                "Avg Tokens": round(avg_tokens, 0),
                "Time (s)": round(process_time, 1),
                "Hit@3": metrics["Hit@3"],
                "Precision@3": metrics["Precision@3"],
                "Recall@3": metrics["Recall@3"],
                "MRR": metrics["MRR"],
            })

    print("\n| Style | Avg Tokens | Time(s) | Hit@3 | Precision@3 | Recall@3 | MRR |")
    print("|---|---|---|---|---|---|---|")
    for r in results_table:
        print(f"| {r['Style']} | {r['Avg Tokens']} | {r['Time (s)']} | {r['Hit@3']:.2f} | {r['Precision@3']:.2f} | {r['Recall@3']:.2f} | {r['MRR']:.2f} |")

    return results_table


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run vision experiments A1–A3.")
    parser.add_argument("--experiment", type=str, choices=["a1", "a2", "a3", "all"], default="all")
    parser.add_argument(
        "--videos",
        nargs="+",
        default=DEFAULT_VIDEOS,
        help="Video paths for A2/A3 (default: all three test videos).",
    )
    args = parser.parse_args()

    # Load existing results so we don't overwrite A2/A3 when running A1, etc.
    out_path = Path("data/experiment_results.json")
    all_results: dict = {}
    if out_path.exists():
        try:
            with open(out_path, "r") as f:
                all_results = json.load(f)
        except json.JSONDecodeError:
            pass

    # A1 is a model-level comparison — runs once on video1, not per-video
    if args.experiment in ["a1", "all"]:
        all_results["A1"] = run_experiment_a1(DEFAULT_VIDEOS[0])

    # A2 and A3 are per-video accuracy experiments
    if args.experiment in ["a2", "a3", "all"]:
        embedder = Embedder()
        for video_path in args.videos:
            video_name = Path(video_path).name
            qa_pairs = VIDEO_QA_PAIRS.get(video_name, [])
            if not qa_pairs:
                print(f"\n[WARN] No QA pairs for '{video_name}' — skipping.")
                continue

            print(f"\n{'='*60}\n  Video: {video_name}  |  QA pairs: {len(qa_pairs)}\n{'='*60}")
            video_results = all_results.get(video_name, {})

            if args.experiment in ["a2", "all"]:
                video_results["A2_SmolVLM"] = run_experiment_a2(video_path, embedder, qa_pairs)

            if args.experiment in ["a3", "all"]:
                video_results["A3_SmolVLM"] = run_experiment_a3(video_path, embedder, qa_pairs)

            all_results[video_name] = video_results

    os.makedirs("data", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {out_path}")

