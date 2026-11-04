package com.eykon.memory.video

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Test
import java.util.Random

/** EYKO-102: the faster ranking and dot product give the same answers as the plain ones they replaced. */
class VideoVectorsRankTest {

    private fun oldRank(scores: FloatArray) = scores.indices.sortedByDescending { scores[it] }.toIntArray()

    @Test
    fun rankingMatchesTheOldSortIncludingTiesAndNegatives() {
        val random = Random(102)
        repeat(200) { round ->
            val n = random.nextInt(2_000)
            // Few distinct values on some rounds, so many scores tie; negatives and both zeros on all.
            val scores = FloatArray(n) {
                if (round % 2 == 0) (random.nextInt(9) - 4) / 4f else random.nextFloat() * 2 - 1
            }
            if (n > 1) { scores[0] = -0f; scores[1] = 0f }
            assertArrayEquals("round $round", oldRank(scores), VideoVectors.rankDescending(scores))
        }
    }

    @Test
    fun rankingOfNothingAndOfOne() {
        assertArrayEquals(IntArray(0), VideoVectors.rankDescending(FloatArray(0)))
        assertArrayEquals(intArrayOf(0), VideoVectors.rankDescending(floatArrayOf(0.5f)))
    }

    @Test
    fun dotWithFourSumsMatchesThePlainLoop() {
        val random = Random(7)
        for (size in listOf(384, 512, 7)) { // 7: a length that is not a multiple of four
            val rows = 50
            val matrix = FloatArray(rows * size) { random.nextFloat() * 2 - 1 }
            val query = FloatArray(size) { random.nextFloat() * 2 - 1 }
            for (r in 0 until rows) {
                var plain = 0f
                for (i in 0 until size) plain += matrix[r * size + i] * query[i]
                assertEquals("size $size row $r", plain, VideoVectors.dot(matrix, r * size, query), 1e-4f)
            }
        }
    }
}
