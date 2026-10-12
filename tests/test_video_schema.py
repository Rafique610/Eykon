import sqlite3

import numpy as np
import pytest

from src.video_memory import db, schema

NOW = "2026-10-12T00:00:00+00:00"


@pytest.fixture
def conn(tmp_path):
    db.clear_cache()
    connection = db.connect(tmp_path / "video.db")
    schema.init_db(connection)
    yield connection
    connection.close()
    db.clear_cache()


def unit(rng, dim=512):
    v = rng.standard_normal(dim).astype(np.float32)
    return v / np.linalg.norm(v)


def add_video(conn, video_id="v1"):
    conn.execute(
        "INSERT INTO videos (video_id, file_path, recorded_at, created_at) VALUES (?, ?, ?, ?)",
        (video_id, f"{video_id}.mp4", NOW, NOW),
    )


def add_frame(conn, frame_no, video_id="v1"):
    return conn.execute(
        "INSERT INTO frames (video_id, frame_no, t_s, path) VALUES (?, ?, ?, ?)",
        (video_id, frame_no, frame_no / 2, f"{frame_no:06d}.jpg"),
    ).lastrowid


def test_init_db_twice_changes_nothing(conn):
    def objects():
        return conn.execute("SELECT type, name, sql FROM sqlite_master ORDER BY name").fetchall()

    before = [tuple(r) for r in objects()]
    schema.init_db(conn)
    assert [tuple(r) for r in objects()] == before
    names = {r[1] for r in before}
    assert set(schema.TABLES) <= names


def test_frame_needs_an_existing_video(conn):
    add_video(conn)
    add_frame(conn, 1)
    with pytest.raises(sqlite3.IntegrityError):
        add_frame(conn, 1, video_id="missing")


def test_put_vector_and_knn(conn):
    rng = np.random.default_rng(1)
    add_video(conn)
    vectors = {add_frame(conn, n): unit(rng) for n in range(3)}
    for frame_id, vec in vectors.items():
        db.put_vector(conn, "image_vec", frame_id, vec)

    wanted = list(vectors)[1]
    hits = db.knn(conn, "image_vec", vectors[wanted], k=3)
    assert hits[0][0] == wanted
    assert hits[0][1] == pytest.approx(1.0, abs=1e-5)
    assert len(hits) == 3

    # a later write is visible: the in-memory copy was refreshed
    new_id, new_vec = add_frame(conn, 99), unit(rng)
    db.put_vector(conn, "image_vec", new_id, new_vec)
    assert db.knn(conn, "image_vec", new_vec, k=1)[0][0] == new_id


def test_put_vector_rejects_the_wrong_size(conn):
    add_video(conn)
    frame_id = add_frame(conn, 1)
    with pytest.raises(ValueError):
        db.put_vector(conn, "image_vec", frame_id, unit(np.random.default_rng(2), dim=384))


def test_knn_on_an_empty_table(conn):
    assert db.knn(conn, "audio_vec", unit(np.random.default_rng(3)), k=5) == []


def test_keyword_search_finds_a_video_text(conn):
    add_video(conn)
    conn.execute(
        "INSERT INTO video_texts (video_id, source, ref_id, start_s, end_s, text) VALUES (?, ?, ?, ?, ?, ?)",
        ("v1", "caption", 1, 0.0, 1.0, "keys on the hall table"),
    )
    found = conn.execute("SELECT rowid FROM video_texts_fts WHERE video_texts_fts MATCH ?", ("keys",)).fetchall()
    assert len(found) == 1


def test_delete_video_leaves_nothing(conn):
    rng = np.random.default_rng(4)
    add_video(conn)
    frame_id = add_frame(conn, 1)
    db.put_vector(conn, "image_vec", frame_id, unit(rng))
    conn.execute("INSERT INTO scene_records (frame_id, objects, caption, source) VALUES (?, ?, ?, ?)", (frame_id, "[]", "a desk", "A"))
    conn.execute("INSERT INTO audio_segments (video_id, start_s, end_s, is_speech, loudness_db) VALUES (?, ?, ?, ?, ?)", ("v1", 0, 1, 1, -20.0))
    conn.execute("INSERT INTO transcript_chunks (video_id, start_s, end_s, text) VALUES (?, ?, ?, ?)", ("v1", 0, 1, "hello"))
    text_id = conn.execute(
        "INSERT INTO video_texts (video_id, source, ref_id, start_s, end_s, text) VALUES (?, ?, ?, ?, ?, ?)",
        ("v1", "transcript", 1, 0.0, 1.0, "hello there"),
    ).lastrowid
    db.put_vector(conn, "text_vec", text_id, unit(rng, dim=384))
    window_id = conn.execute("INSERT INTO audio_windows (video_id, start_s, end_s) VALUES (?, ?, ?)", ("v1", 0, 5)).lastrowid
    db.put_vector(conn, "audio_vec", window_id, unit(rng))
    conn.commit()
    assert db.knn(conn, "image_vec", unit(rng), k=1)  # cached before the delete

    schema.delete_video(conn, "v1")

    for table in schema.TABLES:
        if table == "video_texts_fts":
            left = conn.execute("SELECT COUNT(*) FROM video_texts_fts WHERE video_texts_fts MATCH ?", ("hello",)).fetchone()[0]
        else:
            left = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert left == 0, table
    assert db.knn(conn, "image_vec", unit(rng), k=1) == []
