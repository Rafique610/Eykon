package com.eykon.memory.video

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonObject

/**
 * The test pictures in src/test/resources/filters and the numbers OpenCV gives for them
 * (both written by src/benchmarks/filters_golden.py on the laptop).
 */
object TestPictures {

    val golden: JsonObject by lazy {
        Json.parseToJsonElement(javaClass.getResource("/filters/golden.json")!!.readText()).jsonObject
    }

    /**
     * Reads a test PNG with the desktop Java that runs these tests. Android's own class list has
     * no javax.imageio to compile against, so it is reached by name.
     */
    fun picture(name: String): Gray {
        val image = Class.forName("javax.imageio.ImageIO")
            .getMethod("read", java.net.URL::class.java)
            .invoke(null, javaClass.getResource("/filters/$name.png"))
        val type = image.javaClass
        val width = type.getMethod("getWidth").invoke(image) as Int
        val height = type.getMethod("getHeight").invoke(image) as Int
        val ints = Int::class.javaPrimitiveType
        val argb = type.getMethod("getRGB", ints, ints, ints, ints, IntArray::class.java, ints, ints)
            .invoke(image, 0, 0, width, height, null, 0, width) as IntArray
        return FrameFilters.smallGray(argb, width, height)
    }
}
