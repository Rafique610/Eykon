import subprocess
from pathlib import Path

import pytest

from src.video_memory import db, schema
from src.video_memory.capture import FFMPEG, UploadError, read_metadata, save_upload
from src.video_memory.repository import get_video


class Upload:
    """Stands in for Streamlit's uploaded file: a name, a size and the bytes."""

    def __init__(self, name: str, data: bytes):
        self.name, self.size, self._data = name, len(data), data

    def getvalue(self) -> bytes:
        return self._data


@pytest.fixture(scope="session")
def clip(tmp_path_factory) -> Path:
    """A real 10 s clip with picture and sound, made by ffmpeg itself."""
    path = tmp_path_factory.mktemp("clip") / "test_clip.mp4"
    subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=duration=10:size=640x360:rate=30",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=10", "-shortest", str(path)],
        check=True,
    )
    return path


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMORY_VIDEO_DIR", str(tmp_path / "videos"))
    connection = db.connect(tmp_path / "video.db")
    schema.init_db(connection)
    yield connection
    connection.close()


def videos_on_disk(tmp_path) -> list[Path]:
    return list((tmp_path / "videos").glob("*")) if (tmp_path / "videos").exists() else []


def test_read_metadata_of_a_real_clip(clip):
    meta = read_metadata(clip)
    assert meta["has_video"]
    assert meta["duration_s"] == pytest.approx(10.0, abs=0.2)
    assert meta["lat"] is None and meta["lon"] is None
    assert not meta["from_file"]  # ffmpeg's test clip carries no recording time


def test_save_upload_stores_the_file_and_one_row(conn, clip, tmp_path):
    video, _ = save_upload(conn, Upload("My Clip.MP4", clip.read_bytes()))

    saved = Path(video.file_path)
    assert saved.exists() and saved.name == f"{video.video_id}.mp4"
    assert saved.read_bytes() == clip.read_bytes()
    row = get_video(conn, video.video_id)
    assert row["status"] == "processing"
    assert row["duration_s"] == pytest.approx(10.0, abs=0.2)
    assert conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0] == 1


def test_wrong_type_is_refused_and_creates_nothing(conn, clip, tmp_path):
    with pytest.raises(UploadError, match="not supported"):
        save_upload(conn, Upload("notes.txt", clip.read_bytes()))
    assert conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0] == 0
    assert videos_on_disk(tmp_path) == []


def test_text_renamed_to_mp4_is_refused_and_creates_nothing(conn, tmp_path):
    with pytest.raises(UploadError, match="does not contain a video"):
        save_upload(conn, Upload("fake.mp4", b"this is plain text, not a video"))
    assert conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0] == 0
    assert videos_on_disk(tmp_path) == []


def test_too_big_is_refused_and_creates_nothing(conn, tmp_path, monkeypatch):
    monkeypatch.setenv("MEMORY_VIDEO_MAX_MB", "1")
    with pytest.raises(UploadError, match="limit is 1 MB"):
        save_upload(conn, Upload("big.mp4", b"0" * (5 * 1024 * 1024)))
    assert conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0] == 0
    assert videos_on_disk(tmp_path) == []
