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
