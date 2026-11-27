"""Hypothesis 4 (decision re-check, 26 Nov), laptop half: does madvise(MADV_DONTNEED) on a read-only, shared mapping of the
vector file give the pages back (PSS falls) without changing the next search? Linux, the same kernel call the app's
VectorNative.release makes on Android. Run: uv run --no-project --with numpy python -I src/benchmarks/recheck_release_pages.py
100,000 x 512 float32 (205 MB, the size of one image table at 100k), random unit-scale values; the file is deleted after.
Writes docs/results/recheck-release/release-pages-laptop.json.
"""
import json
import mmap
import os
import tempfile
import time
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[2] / "docs/results/recheck-release"


def pss_mb():
    for line in open("/proc/self/smaps_rollup"):
        if line.startswith("Pss:"):
            return int(line.split()[1]) / 1024


def main(n=100_000, dim=512):
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "t.vec")
        np.random.default_rng(1).standard_normal((n, dim), dtype=np.float32).tofile(path)
        with open(path, "rb") as f:
            m = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            v = np.frombuffer(m, dtype=np.float32).reshape(n, dim)
            q = v[7].copy()
            r = {"file_mb": round(os.path.getsize(path) / 1e6, 1), "pss_before_search_mb": round(pss_mb())}
            t = time.perf_counter(); s1 = v @ q; r["search_ms"] = round((time.perf_counter() - t) * 1e3, 1)
            r["pss_after_search_mb"] = round(pss_mb())
            m.madvise(mmap.MADV_DONTNEED)
            r["pss_after_release_mb"] = round(pss_mb())
            t = time.perf_counter(); s2 = v @ q; r["search_after_release_ms"] = round((time.perf_counter() - t) * 1e3, 1)
            r["pss_after_second_search_mb"] = round(pss_mb())
            r["scores_identical"] = bool(np.array_equal(s1, s2))
            del v
            m.close()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "release-pages-laptop.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    print(json.dumps(r, indent=1))


if __name__ == "__main__":
    main()
