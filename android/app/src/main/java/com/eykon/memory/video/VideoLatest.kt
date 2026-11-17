package com.eykon.memory.video

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Log
import androidx.sqlite.db.SupportSQLiteDatabase
import com.eykon.memory.MemoryApp
import com.eykon.memory.ml.vision.ImageEmbedder
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.float
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import java.io.File
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/** Turns one object's box in a frame file into the vector of its own crop, or null when the box is too small to judge. */
typealias EmbedCrop = (File, List<Float>) -> FloatArray?

/** The same for all the boxes of one frame file at once, in the same order (EYKO-120: the picture is decoded once, not once per box). */
typealias EmbedCrops = (File, List<List<Float>>) -> List<FloatArray?>

/**
 * Stage "latest" (card EYKO-15): every object in a scene record becomes a sighting with a time
 * and a place. Among sightings with the same name, two are the same object when their own crops
 * look alike (cosine of the crop vectors at least [CROP_COSINE_MIN]); the newer one is the
 * latest and the older one keeps its row and says which sighting replaced it. "Where is X now"
 * then reads the latest rows.
 *
 * Objects are what the detector names (people are counted, not listed). Small personal things
 * join when card EYKO-32 is built. Known limits: two things that look the same (two identical
 * chairs) count as one, and a thing moved while the camera was off stays where it was last seen.
 */
object VideoLatest {

    /** Chosen from measured pairs, see docs/results/2026-10-13-eyko-15-crop-threshold.md. */
    const val CROP_COSINE_MIN = 0.87f

    /** A box narrower or lower than this many pixels is too small for its crop to say much. */
    const val MIN_BOX_SIDE = 16
    private const val TAG = "EykonVideo"

    /**
     * Always three decimals of a second. Sightings are put in time order by comparing this text,
     * and a time written sometimes with and sometimes without decimals does not sort by time
     * ("...:28.333Z" would come before "...:28Z").
     */
    private val SEEN_AT = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'").withZone(ZoneOffset.UTC)

    private class Seen(val frameId: Long, val seenAt: String, val place: String?, val label: String, val vector: FloatArray)

    fun run(db: SupportSQLiteDatabase, videoId: String) =
        runFrames(db, videoId, CROP_COSINE_MIN) { file, boxes -> cropVectors(MemoryApp.instance, file, boxes) }

    /** [embedCrop] is the crop's vector; tests pass their own. */
    fun run(db: SupportSQLiteDatabase, videoId: String, minCosine: Float, embedCrop: EmbedCrop) =
        runFrames(db, videoId, minCosine) { file, boxes -> boxes.map { embedCrop(file, it) } }

    private fun runFrames(db: SupportSQLiteDatabase, videoId: String, minCosine: Float, embedCrops: EmbedCrops) {
        val (videoFolder, recordedAt) = db.query("SELECT file_path, recorded_at FROM videos WHERE video_id = ?", arrayOf(videoId)).use { c ->
            if (!c.moveToFirst()) throw IllegalStateException("video $videoId is not in the database")
            (File(c.getString(0)).parentFile ?: throw IllegalStateException("video file has no folder")) to c.getString(1)
        }
        val videosDir = videoFolder.parentFile ?: throw IllegalStateException("video folder has no parent")
        val start = System.nanoTime()
        var tooSmall = 0
        val seen = ArrayList<Seen>()
        db.query(
            "SELECT f.id, f.t_s, f.path, s.objects, s.place FROM frames f JOIN scene_records s ON s.frame_id = f.id WHERE f.video_id = ? AND f.kept = 1 ORDER BY f.t_s",
            arrayOf(videoId),
        ).use { c ->
            while (c.moveToNext()) {
                val file = File(videosDir, c.getString(2))
                val seenAt = SEEN_AT.format(VideoLink.moment(recordedAt, c.getDouble(1)))
                val things = Json.parseToJsonElement(c.getString(3)).jsonArray.map { it.jsonObject }
                val vectors = embedCrops(file, things.map { thing -> thing["box"]!!.jsonArray.map { it.jsonPrimitive.float } })
                for ((thing, vector) in things.zip(vectors)) {
                    if (vector == null) tooSmall++ else seen.add(Seen(c.getLong(0), seenAt, if (c.isNull(4)) null else c.getString(4), thing["label"]!!.jsonPrimitive.content, vector))
                }
            }
        }

        db.beginTransaction()
        try {
            // Idempotent: this video's sightings from an earlier run go first; relink() then restores whatever they had replaced.
            // Per label, the earliest time this run removes or adds a sighting: answers before it cannot change (EYKO-120).
            val from = HashMap<String, String>()
            db.query("SELECT label, MIN(seen_at) FROM object_sightings WHERE video_id = ? GROUP BY label", arrayOf(videoId)).use { c ->
                while (c.moveToNext()) from[c.getString(0)] = c.getString(1)
            }
            for (s in seen) from.merge(s.label, s.seenAt) { a, b -> minOf(a, b) }
            db.execSQL("DELETE FROM object_sightings WHERE video_id = ?", arrayOf(videoId))
            for (s in seen) {
                db.execSQL(
                    "INSERT INTO object_sightings (label, frame_id, video_id, seen_at, place, embedding) VALUES (?, ?, ?, ?, ?, ?)",
                    arrayOf(s.label, s.frameId, videoId, s.seenAt, s.place, VideoVectors.toBlob(s.vector)),
                )
            }
            from.forEach { (label, seenAt) -> relink(db, label, minCosine, seenAt) }
            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
        }
        Log.i(TAG, "latest $videoId: ${seen.size} sightings ($tooSmall boxes too small) in ${(System.nanoTime() - start) / 1_000_000} ms")
    }

    /**
     * Work out afresh which sightings of [label] are the latest, from all videos, oldest first.
     * Going through them in time order (not in the order the videos happened to be processed)
     * gives the same answer whichever video was added first, and an older video can never
     * replace a newer sighting. A sighting replaces the most alike earlier one that is still
     * the latest, provided it is alike enough and from another frame.
     * Only rows whose answer changed are written (EYKO-120: before, every row of the label was rewritten for each video).
     * With [fromSeenAt] (the earliest time a sighting was added or removed), rows before it are not compared again; see [link].
     */
    internal fun relink(db: SupportSQLiteDatabase, label: String, minCosine: Float, fromSeenAt: String? = null) {
        val times = ArrayList<String>()
        val rows = db.query("SELECT id, frame_id, embedding, is_latest, superseded_by, seen_at FROM object_sightings WHERE label = ? ORDER BY seen_at, id", arrayOf(label)).use { c ->
            buildList { while (c.moveToNext()) { add(Link(c.getLong(0), c.getLong(1), VideoVectors.fromBlob(c.getBlob(2)), c.getInt(3) == 1, if (c.isNull(4)) null else c.getLong(4))); times.add(c.getString(5)) } }
        }
        val was = rows.map { it.isLatest to it.supersededBy }
        link(rows, minCosine, if (fromSeenAt == null) 0 else times.indexOfFirst { it >= fromSeenAt }.let { if (it < 0) rows.size else it })
        rows.forEachIndexed { i, row ->
            if (was[i] != (row.isLatest to row.supersededBy)) {
                db.execSQL("UPDATE object_sightings SET is_latest = ?, superseded_by = ? WHERE id = ?", arrayOf(if (row.isLatest) 1 else 0, row.supersededBy, row.id))
            }
        }
    }

    /** One sighting for [link]: its answer (latest, or replaced by which id) is worked out afresh. */
    internal class Link(val id: Long, val frameId: Long, val vector: FloatArray, var isLatest: Boolean = true, var supersededBy: Long? = null)

    /**
     * [rows] in time order. Each row replaces the most alike earlier row that is still the latest and from another frame, if
     * the cosine is at least [minCosine]; on a tie the earlier of the latest rows wins (as maxByOrNull did). Each cosine is
     * worked out once and no list is made per row (EYKO-120).
     *
     * Rows before [from] keep the answer they hold (a later row cannot change an earlier answer), so only rows from [from]
     * on are compared: when a new video is the newest, that is its own sightings against the current latest ones, not the
     * whole label again. The latest rows at [from] are the earlier rows not replaced by an earlier row. This gives the same
     * answer as [from] = 0 when nothing before [from] was added or removed since the answers were written.
     */
    internal fun link(rows: List<Link>, minCosine: Float, from: Int = 0) {
        val position = HashMap<Long, Int>(rows.size * 2)
        rows.forEachIndexed { i, row -> position[row.id] = i }
        val latest = ArrayList<Link>()
        for (i in 0 until from) {
            val row = rows[i]
            val by = row.supersededBy
            if (by == null || (position[by] ?: from) >= from) { row.isLatest = true; row.supersededBy = null; latest.add(row) } else row.isLatest = false
        }
        for (i in from until rows.size) { rows[i].isLatest = true; rows[i].supersededBy = null }
        for (row in rows.subList(from, rows.size)) {
            var best = -1
            var bestCosine = Float.NEGATIVE_INFINITY
            for (i in latest.indices) {
                val other = latest[i]
                if (other.frameId == row.frameId) continue
                val c = cosine(other.vector, row.vector)
                if (best < 0 || c > bestCosine) { best = i; bestCosine = c }
            }
            if (best >= 0 && bestCosine >= minCosine) {
                latest[best].apply { isLatest = false; supersededBy = row.id }
                latest.removeAt(best)
            }
            latest.add(row)
        }
    }

    /** Both vectors have length 1, so the dot product is the cosine. */
    internal fun cosine(a: FloatArray, b: FloatArray): Float {
        var sum = 0f
        for (i in a.indices) sum += a[i] * b[i]
        return sum
    }

    /**
     * The square part of the picture around a box: as wide as the box's longer side, moved to
     * stay inside the picture. Left, top and side in pixels; null when the box is too small.
     */
    internal fun cropSquare(box: List<Float>, width: Int, height: Int): Triple<Int, Int, Int>? {
        val left = max(0f, box[0]); val top = max(0f, box[1])
        val right = min(width.toFloat(), box[2]); val bottom = min(height.toFloat(), box[3])
        if (right - left < MIN_BOX_SIDE || bottom - top < MIN_BOX_SIDE) return null
        val side = min(max(right - left, bottom - top).roundToInt(), min(width, height))
        val x = ((left + right) / 2 - side / 2f).roundToInt().coerceIn(0, width - side)
        val y = ((top + bottom) / 2 - side / 2f).roundToInt().coerceIn(0, height - side)
        return Triple(x, y, side)
    }

    /** The MobileCLIP vector of the object's own part of the frame. */
    fun cropVector(context: Context, file: File, box: List<Float>): FloatArray? = cropVectors(context, file, listOf(box)).single()

    /** The vectors of several objects' own parts of one frame, in order: the picture is decoded once for all of them. */
    fun cropVectors(context: Context, file: File, boxes: List<List<Float>>): List<FloatArray?> {
        if (boxes.isEmpty()) return emptyList()
        val picture = BitmapFactory.decodeFile(file.absolutePath) ?: throw IllegalStateException("picture ${file.name} cannot be read")
        try {
            return boxes.map { box ->
                val (x, y, side) = cropSquare(box, picture.width, picture.height) ?: return@map null
                val crop = Bitmap.createBitmap(picture, x, y, side, side)
                try {
                    ImageEmbedder.embed(context, crop)
                } finally {
                    if (crop !== picture) crop.recycle()
                }
            }
        } finally {
            picture.recycle()
        }
    }
}
