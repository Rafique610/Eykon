package com.eykon.memory.video

import android.content.Context
import android.graphics.BitmapFactory
import com.eykon.memory.ml.vision.DfineDetector
import com.eykon.memory.ml.vision.Detection
import com.eykon.memory.ml.vision.ImageEmbedder
import com.eykon.memory.ml.vision.ObjectDetector
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.float
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import java.io.File
import kotlin.math.exp

/**
 * What one frame shows. Every perception option (A here, B and C later) returns this same shape,
 * so the steps after it do not care which one ran. [caption] is only filled by Option C.
 */
data class Perception(
    val objects: List<Detection>,
    val action: String?,
    val place: String?,
    val people: Int,
    val caption: String? = null,
)

/**
 * Perception Option A (card EYKO-9): describe a frame without a language model. Two detectors
 * list the objects: YOLOX-Tiny (80 COCO things, also counts the people) and D-FINE S (365
 * Objects365 things, card EYKO-32); MobileCLIP scores a fixed list of place and action phrases
 * against the picture. Nothing is written to the database here.
 *
 * The phrases' vectors come from assets/scene_prompts.json, written on the laptop by
 * `task golden-perception` (the phone has no text encoder yet). Changing a phrase means
 * changing the list in src/config.py and running that task again.
 */
object OptionA {

    const val DETECTOR_CONF = 0.35f
    const val PROMPT_MIN = 0.30f
    private const val PROMPTS_ASSET = "scene_prompts.json"

    class Prompts(val texts: List<String>, val vectors: List<FloatArray>)

    private var prompts: Pair<Prompts, Prompts>? = null

    /** The place phrases and the action phrases, read once. */
    @Synchronized
    fun prompts(context: Context): Pair<Prompts, Prompts> = prompts ?: run {
        val json = Json.parseToJsonElement(context.assets.open(PROMPTS_ASSET).bufferedReader().use { it.readText() }).jsonObject
        fun read(key: String): Prompts {
            val entries = json[key]!!.jsonObject
            return Prompts(entries.keys.toList(), entries.values.map { v -> v.jsonArray.map { it.jsonPrimitive.float }.toFloatArray() })
        }
        (read("places") to read("actions")).also { prompts = it }
    }

    /** [imageVector] is the frame's saved MobileCLIP vector when the dedup stage already made one. */
    fun describe(context: Context, file: File, imageVector: FloatArray? = null): Perception {
        val bitmap = BitmapFactory.decodeFile(file.absolutePath) ?: throw IllegalStateException("picture ${file.name} cannot be read")
        try {
            // D-FINE's "person" is left out: it called keys a person on our clips; YOLOX counts the people
            val detections = merge(ObjectDetector.detect(context, bitmap, DETECTOR_CONF), DfineDetector.detect(context, bitmap).filter { it.label != "person" })
            val vector = imageVector ?: ImageEmbedder.embed(context, bitmap)
            val (places, actions) = prompts(context)
            return perception(detections, bestPrompt(vector, places, PROMPT_MIN), bestPrompt(vector, actions, PROMPT_MIN))
        } finally {
            bitmap.recycle()
        }
    }

    /** Kept frames this close in time share their action shares (card EYKO-60, src/config.py scene_action_smooth_s). */
    const val ACTION_SMOOTH_S = 6.0

    /**
     * Each frame's action from the shares averaged over the kept frames within [ACTION_SMOOTH_S] of it,
     * or nothing when the best averaged share is below [PROMPT_MIN]. [vectors] are the frames' picture
     * vectors in [times] order; a frame without one keeps [fallback]'s action.
     */
    internal fun smoothActions(times: List<Double>, vectors: List<FloatArray?>, actions: Prompts, fallback: List<String?>): List<String?> {
        val shares = vectors.map { v -> v?.let { probabilities(it, actions.vectors) } }
        return times.indices.map { i ->
            if (shares[i] == null) return@map fallback[i]
            val near = times.indices.filter { j -> shares[j] != null && kotlin.math.abs(times[j] - times[i]) <= ACTION_SMOOTH_S }
            val mean = FloatArray(actions.texts.size) { a -> near.sumOf { shares[it]!![a].toDouble() }.toFloat() / near.size }
            val best = mean.indices.maxBy { mean[it] }
            if (mean[best] >= PROMPT_MIN) actions.texts[best] else null
        }
    }

    /** YOLOE only looks at a frame whose picture is at least this alike to "a photo of keys" or "a photo of earbuds" (card EYKO-63). */
    const val FLAG_MIN = 0.15f

    private var flags: List<FloatArray>? = null

    @Synchronized
    fun flags(context: Context): List<FloatArray> = flags ?: Json.parseToJsonElement(
        context.assets.open(PROMPTS_ASSET).bufferedReader().use { it.readText() },
    ).jsonObject["small_object_flags"]!!.jsonObject.values.map { v -> v.jsonArray.map { it.jsonPrimitive.float }.toFloatArray() }.also { flags = it }

    /** Whether a frame with this picture vector should get YOLOE; no vector means yes. */
    internal fun flagged(imageVector: FloatArray?, flags: List<FloatArray>): Boolean =
        imageVector == null || flags.any { f -> imageVector.indices.sumOf { (imageVector[it] * f[it]).toDouble() } >= FLAG_MIN }

    /** YOLOX's things, plus D-FINE's unless YOLOX already has the same name for the same place (overlap above 0.5). */
    internal fun merge(yolox: List<Detection>, dfine: List<Detection>): List<Detection> =
        yolox + dfine.filter { d -> yolox.none { it.label == d.label && ObjectDetector.overlap(it.box, d.box) > 0.5f } }

    /** People are counted, not listed: the objects list is for things. */
    internal fun perception(detections: List<Detection>, place: String?, action: String?): Perception =
        Perception(objects = detections.filter { it.label != "person" }, action = action, place = place, people = detections.count { it.label == "person" })

    /** The phrase that fits the picture best, or nothing when even the best one is below [minP]. */
    internal fun bestPrompt(imageVector: FloatArray, prompts: Prompts, minP: Float): String? {
        val p = probabilities(imageVector, prompts.vectors)
        val best = p.indices.maxBy { p[it] }
        return if (p[best] >= minP) prompts.texts[best] else null
    }

    /** How the picture's likeness to each phrase splits into shares that add up to 1 (CLIP's own scale of 100). */
    internal fun probabilities(imageVector: FloatArray, texts: List<FloatArray>): FloatArray {
        val logits = FloatArray(texts.size) { t ->
            var dot = 0f
            for (i in imageVector.indices) dot += imageVector[i] * texts[t][i]
            100 * dot
        }
        val top = logits.max()
        val shares = FloatArray(logits.size) { exp(logits[it] - top) }
        val sum = shares.sum()
        return FloatArray(shares.size) { shares[it] / sum }
    }
}
