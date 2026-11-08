"""Export real vectors from a phone database of our OWN clips into the phone test's assets (EYKO-100).

The vector test pads these to any size with small noise, so every phone runs on the same real
vectors. Never point this at a database with Ego4D clips: the licence forbids sharing anything
from them, and the test APK is shared with the team.

    uv run python src/benchmarks/export_own_vectors.py D:/eykon-cache/frame-report/db/memories.db
"""
import sqlite3
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "android/app/src/androidTest/assets/vectors"


def export(db: Path) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db)
    for table, id_column, dim, name in (("image_vec", "frame_id", 512, "own_image_512.f32"),
                                        ("text_vec", "text_id", 384, "own_text_384.f32")):
        blobs = [row[0] for row in con.execute(f"SELECT embedding FROM {table} ORDER BY {id_column}")]
        assert all(len(b) == dim * 4 for b in blobs), f"{table}: not {dim} float32 numbers"
        (OUT / name).write_bytes(b"".join(blobs))  # same little-endian float32 bytes the app stores
        print(f"{name}: {len(blobs)} vectors from {db}")


if __name__ == "__main__":
    export(Path(sys.argv[1]))
