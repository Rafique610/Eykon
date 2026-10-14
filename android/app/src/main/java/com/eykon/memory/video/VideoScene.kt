package com.eykon.memory.video

import android.util.Log
import androidx.sqlite.db.SupportSQLiteDatabase
import com.eykon.memory.MemoryApp
import com.eykon.memory.ml.vision.Detection
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.float
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import java.io.File

/** Describes one frame file; the second argument is the frame's saved MobileCLIP vector, when there is one. */
typealias Describe = (File, FloatArray?) -> Perception

/**
 * Stage "scene" (card EYKO-10): one scene_records row for every frame that is still kept:
 * the objects, how many people, the place, the action, and a one-line caption in plain words.
 * Whichever perception option runs, the row has the same fields, so later steps do not care.
 */
object VideoScene {

    /** The option that describes frames. B and C join this map when their cards are built. */
    const val SCENE_OPTION = "A"
    val OPTIONS: Map<String, Describe> = mapOf(
        "A" to { file, vector -> OptionA.describe(MemoryApp.instance, file, vector) },
    )
    private const val TAG = "EykonVideo"

    fun run(db: SupportSQLiteDatabase, videoId: String) = run(db, videoId, SCENE_OPTION, OPTIONS.getValue(SCENE_OPTION))

    /** [describe] is the option's function; tests pass their own. */
    fun run(db: SupportSQLiteDatabase, videoId: String, source: String, describe: Describe) {
        val videoFolder = db.query("SELECT file_path FROM videos WHERE video_id = ?", arrayOf(videoId)).use { cursor ->
            if (!cursor.moveToFirst()) throw IllegalStateException("video $videoId is not in the database")
            File(cursor.getString(0)).parentFile ?: throw IllegalStateException("video file has no folder")
        }
        val videosDir = videoFolder.parentFile ?: throw IllegalStateException("video folder has no parent")
        val frames = db.query("SELECT id, path FROM frames WHERE video_id = ? AND kept = 1 ORDER BY t_s", arrayOf(videoId)).use { cursor ->
            buildList { while (cursor.moveToNext()) add(cursor.getLong(0) to cursor.getString(1)) }
        }
        val saved = VideoDedup.readVectors(File(videoFolder, VideoDedup.VECTORS_FILE))

        val start = System.nanoTime()
        val seen = frames.map { (id, path) -> id to describe(File(videosDir, path), saved[id]) }
        val ms = (System.nanoTime() - start) / 1_000_000

        db.beginTransaction()
        try {
            // Idempotent: this video's records from an earlier run go first.
            db.execSQL("DELETE FROM scene_records WHERE frame_id IN (SELECT id FROM frames WHERE video_id = ?)", arrayOf(videoId))
            for ((id, p) in seen) {
                db.execSQL(
                    "INSERT INTO scene_records (frame_id, objects, action, place, people, caption, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    arrayOf(id, objectsJson(p), p.action, p.place, p.people, p.caption ?: buildCaption(p), source),
                )
            }
            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
        }
        Log.i(TAG, "scene $videoId: ${seen.size} frames described by option $source in $ms ms, ${if (seen.isEmpty()) 0 else ms / seen.size} ms each")
    }

    /**
     * Plain words from the fields, no model: up to three different things (the user's own things
     * from OWLv2 first, then surest first), then the people, the place and the action. What is
     * unknown is left out.
     */
    fun buildCaption(p: Perception): String {
        val labels = p.objects.sortedWith(compareByDescending<Detection> { it.source == "owl" }.thenByDescending { it.conf })
            .map { it.label }.distinct().take(3)
        val parts = ArrayList<String>()
        when (labels.size) {
            0 -> Unit
            3 -> parts.add("${labels[0]}, ${labels[1]} and ${labels[2]}")
            else -> parts.add(labels.joinToString(" and "))
        }
        if (p.people > 0) parts.add(if (p.people == 1) "1 person" else "${p.people} people")
        p.place?.let { parts.add(if (it.startsWith("inside ")) it else "in $it") } // "inside a car", not "in inside a car"
        p.action?.let { parts.add(it) }
        return parts.joinToString(", ").ifEmpty { "nothing recognised" }
    }

    /** The objects as JSON text: [{"label": ..., "conf": ..., "box": [left, top, right, bottom], "source": ...}]. */
    internal fun objectsJson(p: Perception): String = buildJsonArray {
        p.objects.forEach { found ->
            add(buildJsonObject {
                put("label", found.label)
                put("conf", found.conf)
                put("box", buildJsonArray { found.box.forEach { add(JsonPrimitive(it)) } })
                put("source", found.source)
            })
        }
    }.toString()

    /** The reverse of [objectsJson]; rows written before "source" existed count as "detector". */
    internal fun objectsFrom(json: String): List<Detection> = Json.parseToJsonElement(json).jsonArray.map { o ->
        val thing = o.jsonObject
        Detection(
            thing["label"]!!.jsonPrimitive.content, thing["conf"]!!.jsonPrimitive.float,
            thing["box"]!!.jsonArray.map { it.jsonPrimitive.float }, thing["source"]?.jsonPrimitive?.content ?: "detector",
        )
    }
}
