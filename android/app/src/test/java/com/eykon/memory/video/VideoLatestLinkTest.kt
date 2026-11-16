package com.eykon.memory.video

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.float
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * EYKO-120: the faster [VideoLatest.link] gives the same answer as the loop it replaced, on the 90 real object crops the Pixel
 * saved for EYKO-15 (labels, frames and MobileCLIP vectors from the phone).
 */
class VideoLatestLinkTest {

    private class Crop(val label: String, val clip: String, val frameNo: Int, val vector: FloatArray)

    private val crops: List<Crop> by lazy {
        val file = File("../../docs/results/latest/pixel9proxl-object-crops-2026-10-13.json")
        Json.parseToJsonElement(file.readText()).jsonObject["crops"]!!.jsonArray.map { it.jsonObject }.map { c ->
            Crop(c["label"]!!.jsonPrimitive.content, c["clip"]!!.jsonPrimitive.content, c["frame_no"]!!.jsonPrimitive.int,
                c["vector"]!!.jsonArray.map { it.jsonPrimitive.float }.toFloatArray())
        }
    }

    /** The loop as it was before EYKO-120, word for word apart from the database: id -> superseded_by. */
    private fun before(rows: List<VideoLatest.Link>, minCosine: Float): Map<Long, Long?> {
        class Row(val id: Long, val frameId: Long, val vector: FloatArray, var supersededBy: Long? = null)
        val all = rows.map { Row(it.id, it.frameId, it.vector) }
        val latest = ArrayList<Row>()
        for (row in all) {
            val same = latest.filter { it.frameId != row.frameId }.maxByOrNull { VideoLatest.cosine(it.vector, row.vector) }
            if (same != null && VideoLatest.cosine(same.vector, row.vector) >= minCosine) {
                same.supersededBy = row.id
                latest.remove(same)
            }
            latest.add(row)
        }
        return all.associate { it.id to it.supersededBy }
    }

    private fun after(rows: List<VideoLatest.Link>, minCosine: Float): Map<Long, Long?> {
        VideoLatest.link(rows, minCosine)
        rows.forEach { assertEquals(it.supersededBy == null, it.isLatest) }
        return rows.associate { it.id to it.supersededBy }
    }

    @Test
    fun theFasterLinkGivesTheSameAnswerOnTheRealPixelCrops() {
        val frames = crops.map { it.clip to it.frameNo }.distinct().sortedWith(compareBy({ it.first }, { it.second }))
        var links = 0
        for (label in crops.map { it.label }.distinct()) {
            val rows = { crops.withIndex().filter { it.value.label == label }
                .sortedWith(compareBy({ it.value.clip }, { it.value.frameNo }, { it.index }))
                .map { VideoLatest.Link(it.index.toLong(), frames.indexOf(it.value.clip to it.value.frameNo).toLong(), it.value.vector) } }
            for (minCosine in listOf(0.80f, 0.85f, VideoLatest.CROP_COSINE_MIN, 0.90f)) {
                val expected = before(rows(), minCosine)
                assertEquals("$label at $minCosine", expected, after(rows(), minCosine))
                if (minCosine == VideoLatest.CROP_COSINE_MIN) links += expected.values.count { it != null }
            }
        }
        assertTrue("the real crops must give some links, or the test proves nothing", links > 0)
    }

    /**
     * The clips are added one by one (in time order, out of order, and with re-runs), as the app does: a re-run removes the
     * clip's rows first. Linking only from the earliest changed time must give what linking the whole label gives.
     */
    @Test
    fun linkingFromTheEarliestChangedTimeGivesTheSameAnswerAsLinkingEverything() {
        val time = compareBy<IndexedValue<Crop>>({ it.value.clip }, { it.value.frameNo }, { it.index })
        val frames = crops.map { it.clip to it.frameNo }.distinct().sortedWith(compareBy({ it.first }, { it.second }))
        val orders = listOf(
            listOf("clip1", "clip2", "clip3", "clip4", "clip5", "clip6"),
            listOf("clip4", "clip1", "clip6", "clip2", "clip5", "clip3"),
            listOf("clip6", "clip5", "clip4", "clip3", "clip2", "clip1"),
            listOf("clip1", "clip2", "clip1", "clip4", "clip3", "clip4", "clip5", "clip6"),
        )
        var skipped = 0
        for (order in orders) {
            val table = HashMap<Int, Long?>() // crop index -> superseded_by, as the database holds it
            for (clip in order) {
                val changed = crops.withIndex().filter { it.value.clip == clip }
                changed.forEach { table[it.index] = null } // removed and added again, or added
                for (label in changed.map { it.value.label }.distinct()) {
                    val start = changed.filter { it.value.label == label }.minWith(time)
                    val inTable = crops.withIndex().filter { it.index in table && it.value.label == label }.sortedWith(time)
                    fun rows() = inTable.map { c ->
                        val by = table[c.index]
                        VideoLatest.Link(c.index.toLong(), frames.indexOf(c.value.clip to c.value.frameNo).toLong(), c.value.vector, by == null, by)
                    }
                    val from = inTable.indexOfFirst { time.compare(it, start) >= 0 }
                    val all = rows().also { VideoLatest.link(it, VideoLatest.CROP_COSINE_MIN) }
                    val part = rows().also { VideoLatest.link(it, VideoLatest.CROP_COSINE_MIN, from) }
                    assertEquals("$order, $clip, $label", all.map { it.supersededBy }, part.map { it.supersededBy })
                    skipped += from
                    all.forEach { table[it.id.toInt()] = it.supersededBy }
                }
            }
        }
        assertTrue("some orders must let rows be skipped, or the test proves nothing", skipped > 0)
    }

    @Test
    fun onATieTheEarlierLatestRowIsReplacedAndAFrameNeverReplacesItself() {
        val v = floatArrayOf(1f, 0f)
        // 1 and 2 share a frame, so both stay latest; 3 ties with both and replaces the earlier one (1);
        // 4 is from 3's frame, so it cannot replace 3 and replaces 2.
        val rows = listOf(VideoLatest.Link(1, 10, v), VideoLatest.Link(2, 10, v), VideoLatest.Link(3, 11, v), VideoLatest.Link(4, 11, v))
        assertEquals(before(rows, 0.87f), after(rows, 0.87f))
        assertEquals(mapOf(1L to 3L, 2L to 4L, 3L to null, 4L to null), after(rows, 0.87f))
    }
}
