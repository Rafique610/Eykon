package com.eykon.memory.video

import android.content.Context
import android.graphics.BitmapFactory
import android.util.Log
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.eykon.memory.ml.vision.DfineDetector
import com.eykon.memory.ml.vision.ObjectDetector
import com.eykon.memory.ml.vision.YoloeDetector
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

/**
 * D-FINE and YOLOE with the real files on this phone, the picture prepared by the app's own code,
 * against what the laptop's processors and the same ONNX files found (detector_golden.json, written
 * by `task phone-detector-assets`). Skipped when a model is not in the phone's models folder.
 */
@RunWith(AndroidJUnit4::class)
class DetectorGoldenTest {

    private val context: Context = ApplicationProvider.getApplicationContext()
    private val testAssets get() = InstrumentationRegistry.getInstrumentation().context.assets
    private val golden by lazy { Json.parseToJsonElement(testAssets.open("detector_golden.json").bufferedReader().readText()).jsonObject }

    private fun picture() = testAssets.open("detector_golden.jpg").use(BitmapFactory::decodeStream)

    @Test
    fun dfineFindsWhatTheLaptopFound() {
        assumeTrue("D-FINE not on this phone", DfineDetector.modelFile(context).exists())
        val laptop = golden["dfine"]!!.jsonArray.map { it.jsonObject }.filter { it["conf"]!!.jsonPrimitive.float >= DfineDetector.MIN_CONF }
        val phone = DfineDetector.detect(context, picture())
        Log.i("EykonVideo", "D-FINE parity: phone ${phone.map { "${it.label} %.3f".format(it.conf) }}")

        assertEquals(laptop.map { DfineDetector.plain(it["label"]!!.jsonPrimitive.content) }, phone.map { it.label })
        laptop.zip(phone).forEach { (expected, found) ->
            assertEquals("${found.label} confidence", expected["conf"]!!.jsonPrimitive.float, found.conf, 0.03f)
        }
    }

    /** YOLOE runs in full precision: the phone's scores match the laptop's (0.000 apart on 50 own frames). */
    @Test
    fun yoloeFindsTheKeysLikeTheLaptop() {
        assumeTrue("YOLOE not on this phone", YoloeDetector.modelFile(context).exists())
        val laptop = golden["yoloe_best"]!!.jsonObject.mapValues { it.value.jsonPrimitive.float }
        val (scores, found) = try {
            YoloeDetector.bestScores(context, picture()) to YoloeDetector.detect(context, picture())
        } finally { YoloeDetector.close() }
        Log.i("EykonVideo", "YOLOE parity: phone $scores, laptop $laptop")

        laptop.forEach { (word, expected) -> assertEquals("$word score", expected, scores.getValue(word), 0.01f) }
        assertEquals(listOf("keys"), found.map { it.label })
        val box = golden["yoloe_keys_box"]!!.jsonArray.map { it.jsonPrimitive.float }
        assertTrue("keys box ${found.single().box} against the laptop's $box", ObjectDetector.overlap(box, found.single().box) > 0.9f)
    }
}
