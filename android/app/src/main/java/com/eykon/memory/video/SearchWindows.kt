package com.eykon.memory.video

/**
 * Card EYKO-58: a search hit becomes a stretch of time, not one frame. From the hit, neighbouring kept
 * frames of the same video join while they score at least [GROW] times the hit and are no more than
 * [GAP_S] apart; the window runs from the first to the last of them, widened by [HALF_S] (each kept
 * frame stands for its 3 s slot). The same rule as src/benchmarks/ego4d_eval.py `windows`, chosen there
 * on Ego4D set A (NLQ objects R@1 at tIoU 0.5: 6.4 % -> 9.0 %; held-out set B 6.2 % -> 15.6 %).
 * Pure Kotlin, so it runs in JVM tests.
 */
object SearchWindows {

    const val GROW = 0.85f
    const val GAP_S = 10.0
    const val HALF_S = 1.5

    /** [times] are the video's kept frames in time order, [scores] their likeness; returns (start s, end s) around frame [hit]. */
    fun grow(times: DoubleArray, scores: FloatArray, hit: Int): Pair<Double, Double> {
        val floor = GROW * scores[hit]
        var lo = hit
        var hi = hit
        while (lo > 0 && scores[lo - 1] >= floor && times[lo] - times[lo - 1] <= GAP_S) lo--
        while (hi < times.size - 1 && scores[hi + 1] >= floor && times[hi + 1] - times[hi] <= GAP_S) hi++
        return (times[lo] - HALF_S).coerceAtLeast(0.0) to times[hi] + HALF_S
    }
}
