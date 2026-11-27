"""Frame-by-frame report of what the phone did with each video, for debugging and for the supervisor.
Reads the phone's own database and frame pictures (nothing is recomputed) and writes one HTML page:
per video, every decoded frame with kept / dropped and the reason, and for each kept frame the boxes,
the objects with scores and which model named them, people, place, action and caption.

    task frame-report -- pull [<video id start>]     copy the database and the frame pictures off the Pixel (adb, run-as)
    task frame-report -- build [<video id start>]    write D:/eykon-cache/frame-report/frame-report.html

With a video id start, only that video. Since EYKO-73 every frame tile also shows the brightness and
sharpness the filter measured (dropped pictures are deleted at finish, so their tiles have numbers, no picture).

Which model named an object: YOLOE finds are stored with source "own". YOLOX-Tiny and D-FINE both
store "detector", so the name decides: a COCO-only name is YOLOX, an Objects365-only name is D-FINE,
a name both know is shown as "YOLOX or D-FINE" (the app does not store more yet).
"""
import base64
import html
import io
import json
import sqlite3
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path("D:/eykon-cache/frame-report")
ADB = [str(Path.home() / "AppData/Local/Android/Sdk/platform-tools/adb.exe"), "-s", "4C031FDAS000NV"]
APP = "com.eykon.memory"
COCO = set(
    "person,bicycle,car,motorcycle,airplane,bus,train,truck,boat,traffic light,fire hydrant,stop sign,parking meter,"
    "bench,bird,cat,dog,horse,sheep,cow,elephant,bear,zebra,giraffe,backpack,umbrella,handbag,tie,suitcase,frisbee,"
    "skis,snowboard,sports ball,kite,baseball bat,baseball glove,skateboard,surfboard,tennis racket,bottle,wine glass,"
    "cup,fork,knife,spoon,bowl,banana,apple,sandwich,orange,broccoli,carrot,hot dog,pizza,donut,cake,chair,couch,"
    "potted plant,bed,dining table,toilet,tv,laptop,mouse,remote,keyboard,cell phone,microwave,oven,toaster,sink,"
    "refrigerator,book,clock,vase,scissors,teddy bear,hair drier,toothbrush".split(","))
COLOURS = {"YOLOX-Tiny": "#2f6fd6", "D-FINE S": "#c2410c", "YOLOX or D-FINE": "#7c3aed", "YOLOE-11L": "#059669"}


def adb(*args: str, binary: bool = False):
    out = subprocess.run(ADB + list(args), capture_output=True, check=True)
    return out.stdout if binary else out.stdout.decode()


def pull(only: str = "") -> None:
    """The database (with its WAL) and every video's frames folder, through run-as (the app's private files)."""
    (ROOT / "db").mkdir(parents=True, exist_ok=True)
    for name in ("memories.db", "memories.db-wal", "memories.db-shm"):
        (ROOT / "db" / name).write_bytes(adb("exec-out", "run-as", APP, "cat", f"databases/{name}", binary=True))
    videos = [v for v in adb("shell", "run-as", APP, "ls", "files/videos").split() if v and v.startswith(only)]
    for v in videos:
        data = adb("exec-out", "run-as", APP, "tar", "-cf", "-", "-C", "files/videos", f"{v}/frames", binary=True)
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            safe = [m for m in tar.getmembers() if m.isfile() and not Path(m.name).is_absolute() and ".." not in Path(m.name).parts]
            tar.extractall(ROOT / "frames", members=safe)  # filter="data" needs Python 3.12; this laptop runs 3.10
        print(v, len(list((ROOT / "frames" / v / "frames").glob("*.jpg"))), "frames")


def measured(bright, sharp) -> str:
    """EYKO-73 numbers; frames filtered before they existed have none."""
    return f"bright {bright:.0f} · sharp {sharp:.0f}" if bright is not None else "not measured"


def model_of(o: dict, o365: set[str]) -> str:
    if o.get("source") in ("own", "owl"):
        return "YOLOE-11L" if o["source"] == "own" else "OWLv2 (old)"
    coco, objects365 = o["label"] in COCO, o["label"] in o365
    return "YOLOX or D-FINE" if coco and objects365 else "YOLOX-Tiny" if coco else "D-FINE S"


def picture(path: Path, width: int, boxes: list[dict] | None = None, o365: set[str] = frozenset()) -> str:
    from PIL import Image, ImageDraw
    image = Image.open(path).convert("RGB")
    if boxes:
        draw = ImageDraw.Draw(image)
        for o in boxes:
            colour = COLOURS.get(model_of(o, o365), "#111")
            draw.rectangle(o["box"], outline=colour, width=3)
            draw.text((o["box"][0] + 4, max(0, o["box"][1] - 12)), f"{o['label']} {o['conf']:.2f}", fill=colour)
    image.thumbnail((width, width))
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=80)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


def build(only: str = "") -> None:
    db = sqlite3.connect(ROOT / "db" / "memories.db")
    plain = (n.split("/")[0].strip().lower() for n in json.loads(Path("android/app/src/main/assets/dfine_labels.json").read_text(encoding="utf-8")))
    o365 = {"keys" if p == "key" else p for p in plain}  # the app's DfineDetector.plain
    videos = db.execute("SELECT video_id, recorded_at, duration_s, status FROM videos WHERE video_id LIKE ? ORDER BY duration_s DESC, created_at", (only + "%",)).fetchall()
    parts = []
    for vid, recorded, duration, status in videos:
        frames = db.execute(
            "SELECT f.id, f.frame_no, f.t_s, f.path, f.kept, f.drop_reason, f.phash, s.objects, s.people, s.place, s.action, s.caption, "
            "(SELECT COUNT(*) FROM image_vec i WHERE i.frame_id = f.id), f.brightness, f.sharpness FROM frames f LEFT JOIN scene_records s ON s.frame_id = f.id "
            "WHERE f.video_id = ? ORDER BY f.frame_no", (vid,)).fetchall()
        latest = {(r[0], r[1]) for r in db.execute("SELECT frame_id, label FROM object_sightings WHERE video_id = ? AND is_latest = 1", (vid,))}
        reasons: dict[str, int] = {}
        strip = []
        for fid, no, t, path, kept, reason, phash, *_, bright, sharp in frames:
            key = "kept" if kept else ("duplicate" if reason and reason.startswith("duplicate") else reason or "dropped")
            reasons[key] = reasons.get(key, 0) + 1
            file = ROOT / "frames" / path
            img = picture(file, 96) if file.exists() else ""
            strip.append(f'<figure class="t {html.escape(key.replace(" ", "-"))}" title="frame {no} · {t:.2f} s · {html.escape(reason or "kept")}">'
                         f'<img loading="lazy" src="{img}" alt="frame {no}"><figcaption>{no} · {t:.1f}s<br>{html.escape(reason or "kept")}<br>{measured(bright, sharp)}</figcaption></figure>')
        cards = []
        for fid, no, t, path, kept, reason, phash, objects, people, place, action, caption, vectors, bright, sharp in frames:
            if not kept:
                continue
            objs = json.loads(objects) if objects else []
            rows = "".join(
                f'<tr><td><span class="dot" style="background:{COLOURS.get(model_of(o, o365), "#111")}"></span>{html.escape(o["label"])}</td>'
                f'<td>{o["conf"]:.2f}</td><td>{html.escape(model_of(o, o365))}</td>'
                f'<td>{", ".join(f"{x:.0f}" for x in o["box"])}</td><td>{"yes" if (fid, o["label"]) in latest else ""}</td></tr>' for o in objs)
            file = ROOT / "frames" / path
            cards.append(
                f'<article class="card"><img src="{picture(file, 640, objs, o365) if file.exists() else ""}" alt="frame {no}">'
                f'<div class="meta"><h4>Frame {no} · {t:.2f} s</h4>'
                f'<p class="cap">“{html.escape(caption or "no caption")}”</p>'
                f'<dl><dt>People (YOLOX)</dt><dd>{people}</dd><dt>Place (MobileCLIP)</dt><dd>{html.escape(place or "none ≥ 0.30")}</dd>'
                f'<dt>Action (MobileCLIP)</dt><dd>{html.escape(action or "none ≥ 0.30")}</dd><dt>dHash</dt><dd><code>{phash}</code></dd>'
                f'<dt>Search vector</dt><dd>{"stored (512-d)" if vectors else "missing"}</dd><dt>Filter measured</dt><dd>{measured(bright, sharp)}</dd></dl>'
                f'<table><thead><tr><th>Object</th><th>Score</th><th>Model</th><th>Box (px)</th><th>Latest</th></tr></thead>'
                f'<tbody>{rows or "<tr><td colspan=5>no objects</td></tr>"}</tbody></table></div></article>')
        counts = " · ".join(f"{k}: {v}" for k, v in sorted(reasons.items(), key=lambda kv: -kv[1]))
        parts.append(f'<section><h2>Video {vid[:8]}</h2><p class="sub">Recorded {recorded} UTC · {duration:.1f} s · status {status} · '
                     f'{len(frames)} frames decoded at 3 per second · {counts}</p>'
                     f'<h3>Every decoded frame</h3><div class="strip">{"".join(strip)}</div>'
                     f'<h3>Kept frames: what each model said</h3>{"".join(cards)}</section>')
    legend = "".join(f'<span><i class="dot" style="background:{c}"></i>{m}</span>' for m, c in COLOURS.items())
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Eykon frame report</title><style>
:root{{--bg:#f7f7f5;--fg:#1c1c1a;--muted:#6b6b66;--card:#fff;--line:#e3e3de}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151514;--fg:#ececea;--muted:#a3a39e;--card:#1f1f1d;--line:#33332f}}}}
body{{margin:0;padding:24px 16px;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif}}
main{{max-width:1180px;margin:auto}} h1{{margin:0 0 4px}} h2{{margin:40px 0 4px;border-top:1px solid var(--line);padding-top:24px}}
.sub,figcaption,dt{{color:var(--muted)}} .legend span{{margin-right:16px;white-space:nowrap}}
.dot{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}}
.strip{{display:grid;grid-template-columns:repeat(auto-fill,minmax(96px,1fr));gap:6px}}
.t{{margin:0;border:3px solid #aaa;border-radius:6px;overflow:hidden;background:var(--card)}} .t img{{width:100%;display:block}}
.t figcaption{{font-size:11px;padding:2px 4px;line-height:1.3}}
.t.kept{{border-color:#059669}} .t.less-sharp{{border-color:#b8b8b2;opacity:.6}} .t.duplicate{{border-color:#d97706}} .t.blurry,.t.dark,.t.bright,.t.still{{border-color:#dc2626}}
.card{{display:grid;grid-template-columns:minmax(0,640px) minmax(0,1fr);gap:16px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px;margin:12px 0}}
@media (max-width:900px){{.card{{grid-template-columns:1fr}}}}
.card img{{width:100%;border-radius:6px}} .cap{{font-size:17px}} dl{{display:grid;grid-template-columns:auto 1fr;gap:2px 12px;margin:8px 0}} dd{{margin:0}}
table{{width:100%;border-collapse:collapse;font-size:14px}} th,td{{text-align:left;padding:4px 6px;border-bottom:1px solid var(--line)}}
</style></head><body><main><h1>Eykon frame report</h1>
<p class="sub">From the Pixel's own database and frame files (nothing recomputed). Frames: green border kept, grey “less sharp” (not the sharpest of its 3 s slot),
orange “duplicate of frame N” (dHash or MobileCLIP cosine ≥ 0.95), red blurry / dark / bright / still. Boxes on kept frames by model:</p>
<p class="legend">{legend}</p><p class="sub">“Latest” = this sighting is the newest of that object across all videos (stage 9). Place and action shown only when MobileCLIP's share is ≥ 0.30.</p>
{"".join(parts)}</main></body></html>"""
    out = ROOT / "frame-report.html"
    out.write_text(page, encoding="utf-8")
    print(out, f"{out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    {"pull": pull, "build": build}[sys.argv[1]](*sys.argv[2:])
