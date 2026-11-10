"""EYKO-91: the recall-with-ties rule and the S1 / S2 vector sources of the laptop benchmark v2."""
import numpy as np
import pytest

from src.benchmarks import _vector_sources as vs


def test_exact_search_scores_one():
    vecs, qs = vs.vectors("random", 2000), vs.queries("random", 5)
    results = [vs.exact_top(vecs, q, 20) for q in qs]
    assert vs.mean_recall(vecs, qs, results) == 1.0


def test_tied_copy_counts_as_hit():
    vecs = vs.vectors("random", 500)
    q = vs.queries("random", 1)[0]
    top = vs.exact_top(vecs, q, 20)
    vecs = np.vstack([vecs, vecs[top[-1]]])  # row 500 = exact copy of the 20th best
    swapped = np.append(top[:-1], 500)
    assert vs.recall_at_k(vecs, q, swapped) == 1.0


def test_wrong_ids_score_below_one():
    vecs = vs.vectors("random", 2000)
    q = vs.queries("random", 1)[0]
    top = vs.exact_top(vecs, q, 20)
    worst = np.argsort(vecs @ q)[:5]
    assert vs.recall_at_k(vecs, q, np.append(top[:15], worst)) == 0.75


def test_repeats_and_missing_ids_do_not_inflate():
    vecs = vs.vectors("random", 1000)
    q = vs.queries("random", 1)[0]
    best = vs.exact_top(vecs, q, 1)[0]
    assert vs.recall_at_k(vecs, q, [best] * 20) == 1 / 20
    assert vs.recall_at_k(vecs, q, [-1] * 20) == 0.0
    assert vs.recall_at_k(vecs, q, vs.exact_top(vecs, q, 10)) == 0.5


@pytest.mark.parametrize("source", ["random", "real"])
def test_sizes_nest_and_vectors_are_unit(source):
    small, large = vs.vectors(source, 1000), vs.vectors(source, 5000)
    np.testing.assert_array_equal(small, large[:1000])
    np.testing.assert_allclose(np.linalg.norm(large, axis=1), 1.0, atol=1e-5)
    assert large.dtype == np.float32
    np.testing.assert_allclose(np.linalg.norm(vs.queries(source, 21), axis=1), 1.0, atol=1e-5)


def test_real_follows_the_phone_recipe():
    base = vs.own_vectors(512)
    vecs = vs.vectors("real", 1000)
    np.testing.assert_array_equal(vecs[: len(base)], base)
    copies = vecs[len(base):]
    cos = np.sum(copies * base[np.arange(len(base), 1000) % len(base)], axis=1)
    assert 0.95 < cos.mean() < 0.99  # noise 0.01 per number, about 0.97 cosine
    assert vs.label("real") == "real_own_clips_90+noise"
    assert vs.label("random") == "random_unit_seed31"


def test_text_table_has_384_numbers():
    assert vs.vectors("real", 200, dim=384).shape == (200, 384)


def test_varied_takes_the_same_spread_rows_for_each_size(tmp_path, monkeypatch):
    rows = np.random.default_rng(0).standard_normal((300, 512)).astype("<f4")
    rows.tofile(tmp_path / "images_512.f32")
    rows[:21].tofile(tmp_path / "queries_512.f32")
    monkeypatch.setattr(vs, "VARIED", tmp_path)
    small, large = vs.vectors("varied", 100), vs.vectors("varied", 300)
    np.testing.assert_allclose(large, rows / np.linalg.norm(rows, axis=1, keepdims=True), rtol=1e-5)
    assert {r.tobytes() for r in small} <= {r.tobytes() for r in large}  # smaller sizes nest
    np.testing.assert_array_equal(small, vs.vectors("varied", 100))  # same rows every run
    picked = [int(np.flatnonzero((large == r).all(axis=1))[0]) for r in small]
    assert picked == sorted(picked) and picked[0] < 30 and picked[-1] > 270  # time order, spans the file
    assert vs.queries("varied", 21).shape == (21, 512)
    with pytest.raises(ValueError, match="epic-vectors"):
        vs.vectors("varied", 301)
    assert vs.label("varied") == "real_epic_kitchens_30_longest_mobileclip_s2"


def test_epic_frame_picking_and_urls():
    from src.benchmarks import embed_epic as ee
    frames = [(i / 59.94, i) for i in range(int(59.94 * 10))]  # 10 s at 59.94 fps
    times = [t for t, _ in ee.pick(frames, 0.745)]
    assert len(times) == 14 and times[0] == 0.0  # 0, 0.745, ... 9.685
    assert all(abs(t - k * 0.745) < 1 / 59.94 and t >= k * 0.745 - 1e-9 for k, t in enumerate(times))
    assert ee.video_urls("P01_109") == ["https://data.bris.ac.uk/datasets/2g1n6qdydwa9u22shpxqzp0t8m/P01/videos/P01_109.MP4"]
    assert [u.split("/")[-3] for u in ee.video_urls("P01_18")] == ["train", "test"]
    assert len(set(ee.VIDEOS)) == 30


def test_remote_file_reads_and_seeks_like_a_local_file():
    import io
    from src.benchmarks import embed_epic as ee
    blob = np.random.default_rng(1).integers(0, 256, 10_000, dtype=np.uint8).tobytes()
    calls = []

    def fetch(url, start, end):
        calls.append(start)
        return blob[start:end]

    f = ee.RemoteFile("x", len(blob), fetch=fetch, workers=3, ahead=4, chunk=1000)
    reader = io.BufferedReader(f, 777)
    assert reader.read(2500) == blob[:2500]
    reader.seek(-10, io.SEEK_END)
    assert reader.read() == blob[-10:]
    reader.seek(4321)
    assert reader.read(3000) == blob[4321:7321]
    assert f.tell() >= 7321 and len(f.jobs) <= 6  # only chunks near the read position are kept
    reader.close()
