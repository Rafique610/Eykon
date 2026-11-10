"""EYKO-117: the Head 3 intake parser (src/benchmarks/head3_intake.py) reads the app's own log lines, in the three formats we get."""

from src.benchmarks import head3_intake as h

VID = "522032dd3efc48428cb2f7a3a0871688"
TIME = f"""--------- beginning of main
11-10 01:17:28.485 I/EykonVideo(17657): split {VID}: 548 frames in 90844 ms (one pass), audio 182.4 s in 29489 ms
11-10 01:17:31.872 I/EykonVideo(17657): filter {VID}: kept 1 of 548 (less sharp 487, still 60) in 3359 ms
11-10 01:17:33.670 I/EykonVideo(17657): dedup {VID}: kept 1 of 1 (hash dropped 0, embedding dropped 0) in 1793 ms; embedded 1 frames, 1747 ms each; memory java 14 MB, native 336 MB
11-10 01:17:36.178 I/EykonVideo(17657): scene {VID}: 1 frames described by option A in 2503 ms, 2503 ms each
11-10 01:17:36.284 I/EykonVideo(17657): small_objects {VID}: 1 frames looked at, 0 found, in 0 ms
11-10 01:17:36.290 I/EykonVideo(17657): embed_images {VID}: 1 vectors stored (1 reused, 0 computed) in 3 ms
11-10 01:17:37.127 I/EykonVideo(17657): embed_texts {VID}: 1 texts (1 captions, 0 transcript chunks) in 835 ms
11-10 01:17:37.130 I/EykonVideo(17657): link {VID}: every row points at its video and moment
11-10 01:17:40.357 I/EykonVideo(17657): latest {VID}: 4 sightings (0 boxes too small) in 3226 ms
11-10 01:17:40.404 I/EykonVideo(17657): finish {VID}: ready; 547 dropped frame files deleted
"""


def rows(video):
    return {stage: (ms, f_in, f_out) for stage, ms, f_in, f_out in video["rows"]}


def test_logcat_time_format():
    v = h.parse_log(TIME)[VID]
    r = rows(v)
    assert v["seconds"] == 182.4 and v["ready"]
    assert r["split_frames"] == (90844, None, 548) and r["split_audio"][0] == 29489
    assert r["filter"] == (3359, 548, 1)
    assert r["dedup"] == (1793, 1, 1)
    assert r["scene"] == (2503, 1, 1)
    assert r["small_objects"] == (0, 1, 0)
    assert r["embed_images"][0] == 3 and r["embed_texts"] == (835, 1, 1)
    assert r["link"] == (None, None, None)
    assert r["latest"] == (3226, None, 4)
    assert v["split_ms"] == 90844 + 29489


def test_threadtime_and_console_formats_give_the_same_rows():
    thread = TIME.replace("I/EykonVideo(17657):", "17657 17657 I EykonVideo:")
    console = "\n".join(line.split(" ", 2)[2] if line[:2].isdigit() else line for line in TIME.splitlines()).replace("I/EykonVideo(17657):", "EykonVideo:")
    assert h.parse_log(thread)[VID]["rows"] == h.parse_log(TIME)[VID]["rows"]
    assert h.parse_log(console)[VID]["rows"] == h.parse_log(TIME)[VID]["rows"]


def test_queue_of_two_videos_and_midnight():
    other = "a" * 32
    text = TIME + TIME.replace(VID, other).replace("11-10 01:", "11-10 00:")  # second set looks earlier: a run past midnight
    videos = h.parse_log(text)
    assert set(videos) == {VID, other}
    assert videos[other]["first"] > videos[VID]["first"]


def test_job_without_a_finish_line_is_not_ready():
    v = h.parse_log(f"11-10 01:00:00.000 I/EykonVideo(1): split {VID}: 10 frames in 5 ms (one pass), audio 1.0 s in 5 ms\n")[VID]
    assert not v["ready"]  # no finish line: the summary counts it as unfinished


def test_copy_line_gives_copy_and_hash_time():
    text = f"11-10 01:00:00.000 I/EykonVideo(1): copy {VID}: 26832141 bytes in 208 ms (hash 22 ms)\n" + TIME
    v = h.parse_log(text)[VID]
    assert v["copy_ms"] == 208
    assert ("copy", 208, None, None) in v["rows"] and ("hash", 22, None, None) in v["rows"]


def test_refused_duplicate_is_not_an_unfinished_video():
    dup = "b" * 32
    videos = h.parse_log(TIME + f"11-10 01:20:00.000 I/EykonVideo(1): copy {dup}: 100 bytes in 5 ms (hash 1 ms)\n")
    assert videos[dup]["started"] is False and videos[VID]["ready"]


def test_backfill_marks_one_finished_video(tmp_path):
    import sqlite3
    from types import SimpleNamespace

    db = tmp_path / "memories.db"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE jobs (id INTEGER PRIMARY KEY, video_id TEXT, status TEXT, stage TEXT)")
    con.executemany("INSERT INTO jobs (video_id, status, stage) VALUES (?, ?, ?)", [("a" * 32, "done", "finish"), ("b" * 32, "done", "finish"), ("c" * 32, "running", "scene")])
    con.commit()
    con.close()
    assert h.cmd_backfill(SimpleNamespace(db=str(db), video_id="b" * 32, stage="latest")) == 0
    con = sqlite3.connect(str(db))
    assert con.execute("SELECT video_id, stage FROM jobs ORDER BY id").fetchall() == [("a" * 32, "finish"), ("b" * 32, "latest"), ("c" * 32, "scene")]
    assert h.cmd_backfill(SimpleNamespace(db=str(db), video_id=None, stage="link")) == 0  # newest finished video (b)
    assert con.execute("SELECT stage FROM jobs WHERE video_id = ?", ("b" * 32,)).fetchone()[0] == "link"
