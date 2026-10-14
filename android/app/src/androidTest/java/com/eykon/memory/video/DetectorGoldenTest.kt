package com.eykon.memory.video

import android.content.Context
import android.graphics.BitmapFactory
import android.util.Log
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.eykon.memory.ml.vision.DfineDetector
import com.eykon.memory.ml.vision.OwlDetector
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
 * D-FINE and OWLv2 with the real files on this phone, the picture prepared by the app's own code,
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

    /** The phone's 8-bit maths gives lower OWLv2 scores than the laptop's (up to 0.32), so only "found or not" is checked. */
    @Test
    fun owlFindsTheKeysAndNoEarbuds() {
        assumeTrue("OWLv2 not on this phone", OwlDetector.modelFile(context).exists())
        val phone = try { OwlDetector.detect(context, picture()) } finally { OwlDetector.close() }
        Log.i("EykonVideo", "OWLv2 parity: phone ${phone.map { "${it.label} %.3f".format(it.conf) }}, laptop ${golden["owl_best"]}")

        assertEquals(listOf("keys"), phone.map { it.label })
        val box = phone.single().box
        assertTrue("keys box $box should be near the middle of the desk", box[0] < 320f && box[2] > 280f && box[1] < 200f && box[3] > 160f)
    }
}
