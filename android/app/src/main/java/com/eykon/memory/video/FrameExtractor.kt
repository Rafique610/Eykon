package com.eykon.memory.video

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.graphics.Matrix
import android.graphics.Rect
import android.graphics.YuvImage
import android.media.Image
import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaExtractor
import android.media.MediaFormat
import android.media.MediaMetadataRetriever
import java.io.ByteArrayOutputStream
import java.io.File
import kotlin.math.ceil
import kotlin.math.max

/** Pulls the frames nearest to the wanted times out of a video and saves them as JPEGs. */
object FrameExtractor {

    /**
     * One pass through the video with the phone's decoder, keeping the first frame at or after
     * each wanted time. Returns (frame number from 1, wanted time) for every frame saved.
     * Frames are shrunk by a whole-number factor so the longer side is at most [maxSide].
     */
    /** Where one pass spends its time; everything not in these two is the decoder itself. */
    class Timing { var convertNs = 0L; var writeNs = 0L }

    fun decodeInOnePass(
        filePath: String, framesDir: File, times: List<Double>, maxSide: Int, quality: Int, timing: Timing? = null,
    ): List<Pair<Int, Double>> {
        val saved = ArrayList<Pair<Int, Double>>(times.size)
        if (times.isEmpty()) return saved
        val extractor = MediaExtractor()
        try {
            VideoSource.setOn(extractor, filePath)
            val track = (0 until extractor.trackCount).firstOrNull {
                extractor.getTrackFormat(it).getString(MediaFormat.KEY_MIME)?.startsWith("video/") == true
            } ?: throw IllegalStateException("the file has no video track")
            val format = extractor.getTrackFormat(track)
            val rotation = if (format.containsKey(MediaFormat.KEY_ROTATION)) format.getInteger(MediaFormat.KEY_ROTATION) else 0
            format.setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Flexible)
            extractor.selectTrack(track)

            val codec = MediaCodec.createDecoderByType(format.getString(MediaFormat.KEY_MIME)!!)
            try {
                // Not playback: ask the decoder for its full speed, not real time. The frames are the same; a decoder that refuses
                // the hint is configured again without it.
                try {
                    codec.configure(MediaFormat(format).apply { setInteger(MediaFormat.KEY_OPERATING_RATE, Short.MAX_VALUE.toInt()) }, null, null, 0)
                } catch (e: Exception) {
                    codec.reset()
                    codec.configure(format, null, null, 0)
                }
                codec.start()
                val info = MediaCodec.BufferInfo()
                var next = 0
                var inputDone = false
                while (next < times.size) {
                    if (!inputDone) {
                        val inIndex = codec.dequeueInputBuffer(0)
                        if (inIndex >= 0) {
                            val size = extractor.readSampleData(codec.getInputBuffer(inIndex)!!, 0)
                            if (size < 0) {
                                codec.queueInputBuffer(inIndex, 0, 0, 0, MediaCodec.BUFFER_FLAG_END_OF_STREAM)
                                inputDone = true
                            } else {
                                codec.queueInputBuffer(inIndex, 0, size, extractor.sampleTime, 0)
                                extractor.advance()
                            }
                        }
                    }
                    val outIndex = codec.dequeueOutputBuffer(info, if (inputDone) 10_000 else 500)
                    if (outIndex < 0) continue
                    if (info.size > 0 && info.presentationTimeUs / 1e6 >= times[next] - 1e-3) {
                        val image = codec.getOutputImage(outIndex)
                            ?: throw IllegalStateException("the decoder gives no readable image")
                        val t0 = System.nanoTime()
                        val jpeg = image.use { toJpeg(it, maxSide, quality) }.let { if (rotation == 0) it else rotate(it, rotation, quality) }
                        val t1 = System.nanoTime()
                        val frameNo = next + 1
                        File(framesDir, "%06d.jpg".format(frameNo)).writeBytes(jpeg)
                        timing?.apply { convertNs += t1 - t0; writeNs += System.nanoTime() - t1 }
                        saved.add(frameNo to times[next])
                        next++
                    }
                    codec.releaseOutputBuffer(outIndex, false)
                    if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) break
                }
            } finally {
                codec.stop()
                codec.release()
            }
        } finally {
            extractor.release()
        }
        return saved
    }

    /** The simple way: ask the system for each frame in turn. Much slower; used when one pass is not possible. */
    fun seekEachFrame(filePath: String, framesDir: File, times: List<Double>, maxSide: Int, quality: Int): List<Pair<Int, Double>> {
        val retriever = MediaMetadataRetriever()
        try {
            VideoSource.setOn(retriever, filePath)
            val saved = ArrayList<Pair<Int, Double>>(times.size)
            times.forEachIndexed { index, t ->
                val bitmap = retriever.getScaledFrameAtTime((t * 1_000_000).toLong(), MediaMetadataRetriever.OPTION_CLOSEST, maxSide, maxSide)
                    ?: return@forEachIndexed // a time the reader cannot decode (can happen at the very end)
                val frameNo = index + 1
                File(framesDir, "%06d.jpg".format(frameNo)).outputStream().use { bitmap.compress(Bitmap.CompressFormat.JPEG, quality, it) }
                bitmap.recycle()
                saved.add(frameNo to t)
            }
            return saved
        } finally {
            retriever.release()
        }
    }

    /** A decoder image (YUV 4:2:0) to JPEG bytes, keeping every k-th pixel so the longer side fits [maxSide]. */
    private fun toJpeg(image: Image, maxSide: Int, quality: Int): ByteArray {
        val crop = image.cropRect
        val k = max(1, ceil(max(crop.width(), crop.height()) / maxSide.toDouble()).toInt())
        val width = (crop.width() / k) and 1.inv()
        val height = (crop.height() / k) and 1.inv()
        val (yPlane, uPlane, vPlane) = image.planes
        val nv21 = ByteArray(width * height * 3 / 2)

        // Each needed row is copied out in one bulk read, then every k-th byte is picked from it: the same pixels as reading the
        // buffer one byte at a time (about 350,000 calls a frame), so the same JPEG bytes, in a fraction of the time.
        val y = yPlane.buffer.duplicate()
        val yStep = k * yPlane.pixelStride
        val yRow = ByteArray((width - 1) * yStep + 1)
        for (row in 0 until height) {
            y.position((crop.top + row * k) * yPlane.rowStride + crop.left * yPlane.pixelStride)
            y.get(yRow)
            val target = row * width
            for (col in 0 until width) nv21[target + col] = yRow[col * yStep]
        }
        val u = uPlane.buffer.duplicate()
        val v = vPlane.buffer.duplicate()
        val uStep = k * uPlane.pixelStride
        val vStep = k * vPlane.pixelStride
        val uRow = ByteArray((width / 2 - 1) * uStep + 1)
        val vRow = ByteArray((width / 2 - 1) * vStep + 1)
        for (row in 0 until height / 2) {
            val chromaRow = crop.top / 2 + row * k
            u.position(chromaRow * uPlane.rowStride + crop.left / 2 * uPlane.pixelStride)
            u.get(uRow)
            v.position(chromaRow * vPlane.rowStride + crop.left / 2 * vPlane.pixelStride)
            v.get(vRow)
            val target = width * height + row * width
            for (col in 0 until width / 2) {
                nv21[target + 2 * col] = vRow[col * vStep]
                nv21[target + 2 * col + 1] = uRow[col * uStep]
            }
        }
        return ByteArrayOutputStream().also {
            YuvImage(nv21, ImageFormat.NV21, width, height, null).compressToJpeg(Rect(0, 0, width, height), quality, it)
        }.toByteArray()
    }

    /** Phone videos shot upright are stored sideways with a rotation note; turn the picture the right way up. */
    private fun rotate(jpeg: ByteArray, degrees: Int, quality: Int): ByteArray {
        val bitmap = BitmapFactory.decodeByteArray(jpeg, 0, jpeg.size)
        val turned = Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, Matrix().apply { postRotate(degrees.toFloat()) }, true)
        return ByteArrayOutputStream().also { turned.compress(Bitmap.CompressFormat.JPEG, quality, it) }.toByteArray().also {
            bitmap.recycle()
            turned.recycle()
        }
    }
}
