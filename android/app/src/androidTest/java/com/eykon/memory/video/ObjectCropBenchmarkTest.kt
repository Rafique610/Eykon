package com.eykon.memory.video

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.media.MediaMetadataRetriever
import androidx.sqlite.db.SupportSQLiteDatabase
import androidx.sqlite.db.SupportSQLiteOpenHelper
import androidx.sqlite.db.framework.FrameworkSQLiteOpenHelperFactory
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.eykon.memory.ml.vision.ImageEmbedder
import com.eykon.memory.ml.vision.ObjectDetector
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.float
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/**
 * Card EYKO-15, the data for choosing the crop threshold: every clip in files/eval_clips goes
 * through the app's stages up to the scene records, then every object's own crop is saved as a
 * picture in files/object_crops with its vector in files/object_crops.json. A person then says
 * which crops show the same object, and src/benchmarks/crop_pairs.py compares the vectors.
 * Not a pass/fail test; skipped when the clips or a model are not on the phone.
 */
@RunWith(AndroidJUnit4::class)
class ObjectCropBenchmarkTest {

    private val context: Context = ApplicationProvider.getApplicationContext()

    @Test
    fun saveEveryObjectCrop() {
        val clips = File(context.getExternalFilesDir(null), "eval_clips").listFiles { f -> f.extension.lowercase() == "mp4" }?.sortedBy { it.name }.orEmpty()
        assumeTrue("no clips in files/eval_clips", clips.isNotEmpty())
        assumeTrue("a model is not on this phone", ObjectDetector.modelFile(context).exists() && ImageEmbedder.modelFile(context).exists())

        val work = File(context.cacheDir, "crop_bench").apply { deleteRecursively(); mkdirs() }
        val out = File(context.getExternalFilesDir(null), "object_crops").apply { deleteRecursively(); mkdirs() }
        val callback = object : SupportSQLiteOpenHelper.Callback(1) {
            override fun onConfigure(db: SupportSQLiteDatabase) = db.setForeignKeyConstraintsEnabled(true)
            override fun onCreate(db: SupportSQLiteDatabase) = VideoSchema.create(db)
            override fun onUpgrade(db: SupportSQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit
        }
        val helper = FrameworkSQLiteOpenHelperFactory().create(SupportSQLiteOpenHelper.Configuration.builder(context).name(null).callback(callback).build())
        val db = helper.writableDatabase
        var tooSmall = 0
        var embedNs = 0L

        val crops = buildJsonArray {
            for (clip in clips) {
                val id = clip.nameWithoutExtension
                val folder = File(work, id).apply { mkdirs() }
                val copy = File(folder, "$id.mp4").also { clip.copyTo(it, overwrite = true) }
                val length = MediaMetadataRetriever().run { setDataSource(copy.absolutePath); (extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)!!.toLong() / 1000.0).also { release() } }
                VideoRepository { db }.insert(Video(videoId = id, filePath = copy.absolutePath, recordedAt = "2026-10-13T00:00:00Z", createdAt = "2026-10-13T00:00:00Z", durationS = length))
                VideoSplit.run(db, id); VideoFilter.run(db, id); VideoDedup.run(db, id); VideoScene.run(db, id)
                db.query("SELECT f.frame_no, f.path, s.objects FROM frames f JOIN scene_records s ON s.frame_id = f.id WHERE f.video_id = ? AND f.kept = 1 ORDER BY f.t_s", arrayOf(id)).use { c ->
                    while (c.moveToNext()) {
                        val file = File(work, c.getString(1))
                        val picture = BitmapFactory.decodeFile(file.absolutePath)
                        kotlinx.serialization.json.Json.parseToJsonElement(c.getString(2)).jsonArray.forEachIndexed { n, thing ->
                            val label = thing.jsonObject["label"]!!.jsonPrimitive.content
                            val box = thing.jsonObject["box"]!!.jsonArray.map { it.jsonPrimitive.float }
                            val square = VideoLatest.cropSquare(box, picture.width, picture.height)
                            if (square == null) { tooSmall++; return@forEachIndexed }
                            val name = "${id}_%06d_%d_%s.jpg".format(c.getInt(0), n, label.replace(' ', '-'))
                            Bitmap.createBitmap(picture, square.first, square.second, square.third, square.third).let { crop ->
                                File(out, name).outputStream().use { crop.compress(Bitmap.CompressFormat.JPEG, 90, it) }
                            }
                            val start = System.nanoTime()
                            val vector = VideoLatest.cropVector(context, file, box)!!
                            embedNs += System.nanoTime() - start
                            add(buildJsonObject {
                                put("crop", name); put("clip", id); put("frame_no", c.getInt(0)); put("label", label)
                                put("conf", thing.jsonObject["conf"]!!.jsonPrimitive.float); put("side", square.third)
                                put("vector", buildJsonArray { vector.forEach { add(JsonPrimitive(Math.round(it * 1e6f) / 1e6f)) } })
                            })
                        }
                        picture.recycle()
                    }
                }
            }
        }
        helper.close()
        work.deleteRecursively()
        File(context.getExternalFilesDir(null), "object_crops.json").writeText(buildJsonObject {
            put("device", "${android.os.Build.MANUFACTURER} ${android.os.Build.MODEL}")
            put("min_box_side", VideoLatest.MIN_BOX_SIDE); put("boxes_too_small", tooSmall)
            put("ms_per_crop", if (crops.isEmpty()) 0.0 else embedNs / 1e6 / crops.size)
            put("crops", crops)
        }.toString())
    }
}
