package com.eykon.memory.video

import android.content.Context
import android.graphics.BitmapFactory
import android.util.Log
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.eykon.memory.ml.vision.ImageEmbedder
import com.eykon.memory.ml.vision.ObjectDetector
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.float
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/**
 * Perception Option A with the real models on this phone, against what the laptop got for the
 * same picture (perception_golden.json, written by `task golden-perception`).
 * Skipped when yolox_tiny.onnx or mobileclip_s2_image.onnx is not in the phone's models folder.
 */
@RunWith(AndroidJUnit4::class)
class OptionAPhoneTest {

    private val context: Context = ApplicationProvider.getApplicationContext()
    private val testAssets get() = InstrumentationRegistry.getInstrumentation().context.assets
    private val golden by lazy { Json.parseToJsonElement(testAssets.open("perception_golden.json").bufferedReader().readText()).jsonObject }
    private val pictureName get() = golden["picture"]!!.jsonPrimitive.content

    private fun picture() = testAssets.open("perception/$pictureName").use(BitmapFactory::decodeStream)

    @Test
    fun thePhoneFindsTheSameObjectsAsTheLaptop() {
        assumeTrue("detector not on this phone", ObjectDetector.modelFile(context).exists())
        val laptop = golden["detections"]!!.jsonArray.map { it.jsonObject }
        val phone = ObjectDetector.detect(context, picture(), OptionA.DETECTOR_CONF)
        Log.i("EykonVideo", "detector parity: phone ${phone.map { "${it.label} %.3f".format(it.conf) }}")

        assertEquals(laptop.map { it["label"]!!.jsonPrimitive.content }, phone.map { it.label })
        laptop.zip(phone).forEach { (expected, found) ->
            assertEquals("${found.label} confidence", expected["conf"]!!.jsonPrimitive.float, found.conf, 0.03f)
            val overlap = ObjectDetector.overlap(expected["box"]!!.jsonArray.map { it.jsonPrimitive.float }, found.box)
            assertTrue("${found.label} box overlaps the laptop's only $overlap", overlap > 0.95f)
        }
    }

    @Test
    fun placeAndActionSharesMatchTheLaptop() {
        assumeTrue("image model not on this phone", ImageEmbedder.modelFile(context).exists())
        val vector = ImageEmbedder.embed(context, picture())
        val (places, actions) = OptionA.prompts(context)
        val scene = golden["scene"]!!.jsonObject

        for ((name, prompts) in listOf("place" to places, "action" to actions)) {
            val laptop = scene["${name}_p"]!!.jsonArray.map { it.jsonPrimitive.float }
            val phone = OptionA.probabilities(vector, prompts.vectors)
            Log.i("EykonVideo", "$name parity: phone ${phone.map { "%.3f".format(it) }} laptop $laptop")
            assertEquals(laptop.size, phone.size)
            laptop.indices.forEach { assertEquals("$name ${prompts.texts[it]}", laptop[it], phone[it], 0.08f) }
            assertEquals(scene[name]!!.jsonPrimitive.content, OptionA.bestPrompt(vector, prompts, OptionA.PROMPT_MIN))
        }
    }

    @Test
    fun aFrameFileIsDescribedInOneCall() {
        assumeTrue("models not on this phone", ObjectDetector.modelFile(context).exists() && ImageEmbedder.modelFile(context).exists())
        val file = File(context.cacheDir, pictureName)
        testAssets.open("perception/$pictureName").use { input -> file.outputStream().use { input.copyTo(it) } }
        try {
            val seen = OptionA.describe(context, file)
            val again = OptionA.describe(context, file, ImageEmbedder.embed(context, file))

            // YOLOX's things come first; D-FINE's extra ones (card EYKO-32) follow them
            val yolox = golden["detections"]!!.jsonArray.map { it.jsonObject["label"]!!.jsonPrimitive.content }
            assertEquals(yolox, seen.objects.take(yolox.size).map { it.label })
            assertEquals(0, seen.people)
            assertEquals(golden["scene"]!!.jsonObject["place"]!!.jsonPrimitive.content, seen.place)
            assertEquals(null, seen.caption)
            assertEquals(seen, again) // a saved vector gives the same answer as embedding the frame again
        } finally {
            file.delete()
        }
    }
}
