"""Pick Ego4D episodic-memory validation clips for a test set (cards EYKO-54, EYKO-57).
    task ego4d-select -- <set name> [<earlier set name> ...]

The rule of set A (19 October, D:/eykon-cache/ego4d/selection/ego_pick2.py), applied to videos no earlier set
used: among videos that have NLQ, VQ and MQ clips, the 8 MQ clips with the most of our action classes, then the
8 NLQ clips with the most questions and the 8 VQ clips with the most valid queries from those same videos.
Writes D:/eykon-cache/ego4d/sets/<set>/clip_uids.txt and video_uids.txt. Set A lives in selection/.
"""
import json
import re
import sys
from pathlib import Path

EGO = Path("D:/eykon-cache/ego4d")
ANN = EGO / "v2/annotations"
OURS = re.compile(r"eat|drink|typ|laptop|computer|cook|stir|wash|walk|run|read|writ|phone|talk|convers|stair")


def load(task: str) -> list[dict]:
    rows = []
    for v in json.loads((ANN / f"{task}_val.json").read_text())["videos"]:
        for c in v["clips"]:
            items = []
            for a in c["annotations"]:
                for k in ("language_queries", "query_sets", "labels"):
                    x = a.get(k)
                    if x:
                        items += x if isinstance(x, list) else list(x.values())
            rows.append({"clip": c["clip_uid"], "video": v["video_uid"], "items": items})
    return rows


def set_dir(name: str) -> Path:
    return EGO / "selection" if name == "A" else EGO / "sets" / name


def main(name: str, earlier: list[str]) -> None:
    used = {v for e in earlier for v in (set_dir(e) / "video_uids.txt").read_text().split()}
    nlq, vq, mq = load("nlq"), load("vq"), load("moments")
    videos = lambda rows: {r["video"] for r in rows} - used
    shared = videos(nlq) & videos(vq) & videos(mq)
    mq_pick = sorted((r for r in mq if r["video"] in shared), key=lambda r: len({lab["label"] for lab in r["items"] if OURS.search(lab["label"])}), reverse=True)[:8]
    vids = {r["video"] for r in mq_pick}
    nlq_pick = sorted((r for r in nlq if r["video"] in vids), key=lambda r: len(r["items"]), reverse=True)[:8]
    vq_pick = sorted((r for r in vq if r["video"] in vids), key=lambda r: sum(1 for q in r["items"] if q.get("is_valid")), reverse=True)[:8]
    out = set_dir(name)
    out.mkdir(parents=True, exist_ok=True)
    uids = sorted({r["clip"] for r in mq_pick + nlq_pick + vq_pick})
    (out / "clip_uids.txt").write_text("\n".join(uids), encoding="utf-8")
    (out / "video_uids.txt").write_text("\n".join(sorted(vids)), encoding="utf-8")
    print(f"set {name}: {len(uids)} clips from {len(vids)} videos (MQ {len(mq_pick)}, NLQ {len(nlq_pick)}, VQ {len(vq_pick)}), "
          f"{sum(len(r['items']) for r in nlq_pick)} NLQ questions, {sum(len(r['items']) for r in vq_pick)} VQ queries")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
