"""Does the laptop copy (ego4d_pipeline) do what the app did on the Pixel? (card EYKO-56)
    task ego4d-phone-compare -- <pulled memories.db> <map.json: phone video id -> Ego4D clip uid>

Phone videos are matched to Ego4D clips by the exact size of the app's copy of the file (durations of
the 8-minute clips differ by only hundredths of a second, too little to tell them apart). For each pair: kept frames (same second, 0.01 s), and on the
frames both kept the caption, place and action. Phone cost per minute of video comes from the job's
created / updated times, the frames' and database's sizes are read from the pulled copy.
"""
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import cv2

from src.benchmarks.ego4d_pipeline import CLIPS, RUN


def duration(uid: str) -> float:
    cap = cv2.VideoCapture(str(CLIPS / f"{uid}.mp4"))
    d = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    return d


def when(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def main(db_path: str, map_path: str) -> None:
    clip_of = json.loads(Path(map_path).read_text())
    db = sqlite3.connect(db_path)
    videos = db.execute("SELECT v.video_id, v.duration_s, j.created_at, j.updated_at, j.status FROM videos v JOIN jobs j ON j.video_id = v.video_id").fetchall()
    out = []
    for vid, dur, created, updated, status in videos:
        uid = clip_of.get(vid)
        if uid is None:
            continue
        d = duration(uid)
        if status != "done":
            out.append({"clip": uid[:8], "phone": "not finished or not found"})
            continue
        lap = json.loads((RUN / f"{uid}.json").read_text())
        lk = {round(k["t"], 2): k for k in lap["kept"]}
        rows = db.execute("SELECT f.t_s, s.caption, s.place, s.action, s.objects, s.people FROM frames f JOIN scene_records s ON s.frame_id = f.id "
                          "WHERE f.video_id = ? AND f.kept = 1", (vid,)).fetchall()
        pk = {round(t, 2): (cap, place, action, {o["label"] for o in json.loads(objs)}, people) for t, cap, place, action, objs, people in rows}
        both = sorted(set(lk) & set(pk))
        same = lambda i, pk=pk, lk=lk, both=both: sum(pk[t][i] == (lk[t]["caption"], lk[t]["place"], lk[t]["action"])[i] for t in both)
        # jobs run one after another: this one started when it was queued or when the one before it finished
        ends = [when(v[3]) for v in videos if v[4] == "done" and when(v[3]) < when(updated)]
        minutes = (when(updated) - max([when(created)] + ends)).total_seconds() / 60
        names = lambda t, lk=lk: {o["label"] for o in lk[t]["objects"]}
        overlap = [len(pk[t][3] & names(t)) / len(pk[t][3] | names(t)) if pk[t][3] | names(t) else 1.0 for t in both]
        out.append({"clip": uid[:8], "video s": round(d), "kept phone": len(pk), "kept laptop": len(lk), "same second": len(both),
                    "same caption": same(0), "same place": same(1), "same action": same(2),
                    "object names overlap": round(sum(overlap) / max(1, len(overlap)), 2),
                    "same people count": sum(pk[t][4] == lk[t]["people"] for t in both),
                    "phone min": round(minutes, 1), "caption KB": round(sum(len(r[1].encode()) for r in rows) / 1024, 1)})
    for row in out:
        print(row)
    print("database MB", round(sum(p for (p,) in db.execute("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()")) / 1e6, 1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
