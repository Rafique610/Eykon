import re
import shutil
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import imageio_ffmpeg

from src.config import Settings
from src.video_memory.models import Video
from src.video_memory.repository import insert_video

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
ISO6709 = re.compile(r"([+-]\d+\.\d+)([+-]\d+\.\d+)")
DURATION = re.compile(r"Duration: (\d+):(\d+):(\d+\.\d+)")
VIDEO_STREAM = re.compile(r"Stream #\S+.*: Video:")


class UploadError(ValueError):
    """The uploaded file was refused; the message is safe to show to the person."""


def read_metadata(path: Path | str) -> dict:
    """Recording time (UTC ISO), duration, GPS and whether the file really holds video, read by ffmpeg."""
    run = subprocess.run(
        [FFMPEG, "-i", str(path), "-f", "ffmetadata", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    tags = dict(line.split("=", 1) for line in run.stdout.splitlines() if "=" in line and not line.startswith(";"))
    out = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "from_file": False,
        "duration_s": 0.0,
        "lat": None,
        "lon": None,
        "has_video": bool(VIDEO_STREAM.search(run.stderr)),
    }
    if created := tags.get("creation_time"):
        try:
            out["recorded_at"] = datetime.fromisoformat(created.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
            out["from_file"] = True
        except ValueError:
            pass
    place = tags.get("location") or tags.get("com.apple.quicktime.location.ISO6709") or ""
    if m := ISO6709.match(place):
        out["lat"], out["lon"] = float(m[1]), float(m[2])
    if m := DURATION.search(run.stderr):
        out["duration_s"] = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
    return out


def save_upload(conn: sqlite3.Connection, uploaded_file) -> tuple[Video, dict]:
    """Check, store and register one uploaded clip. Returns the video and its metadata."""
    s = Settings()
    ext = Path(uploaded_file.name).suffix.lower().lstrip(".")
    if ext not in s.video_types:
        raise UploadError(f"This file type is not supported. Use one of: {', '.join(s.video_types)}.")
    if uploaded_file.size > s.video_max_mb * 1024 * 1024:
        raise UploadError(f"This file is {uploaded_file.size / 1024 / 1024:.0f} MB. The limit is {s.video_max_mb} MB.")

    video_id = uuid4().hex
    folder = s.video_dir / video_id
    folder.mkdir(parents=True)
    path = folder / f"{video_id}.{ext}"
    try:
        path.write_bytes(uploaded_file.getvalue())
        meta = read_metadata(path)
        if not meta["has_video"]:
            raise UploadError("This file does not contain a video that can be read.")
        video = Video(
            video_id=video_id,
            file_path=path.as_posix(),
            recorded_at=meta["recorded_at"],
            created_at=datetime.now(timezone.utc).isoformat(),
            duration_s=meta["duration_s"],
            lat=meta["lat"],
            lon=meta["lon"],
        )
        with conn:
            insert_video(conn, video)
    except BaseException:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    return video, meta
