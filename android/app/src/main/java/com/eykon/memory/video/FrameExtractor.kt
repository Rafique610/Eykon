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
    fun decodeInOnePass(filePath: String, framesDir: File, times: List<Double>, maxSide: Int, quality: Int): List<Pair<Int, Double>> {
        val saved = ArrayList<Pair<Int, Double>>(times.size)
        if (times.isEmpty()) return saved
        val extractor = MediaExtractor()
        try {
            extractor.setDataSource(filePath)
            val track = (0 until extractor.trackCount).firstOrNull {
                extractor.getTrackFormat(it).getString(MediaFormat.KEY_MIME)?.startsWith("video/") == true
            } ?: throw IllegalStateException("the file has no video track")
            val format = extractor.getTrackFormat(track)
            val rotation = if (format.containsKey(MediaFormat.KEY_ROTATION)) format.getInteger(MediaFormat.KEY_ROTATION) else 0
            format.setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Flexible)
            extractor.selectTrack(track)

            val codec = MediaCodec.createDecoderByType(format.getString(MediaFormat.KEY_MIME)!!)
            try {
                codec.configure(format, null, null, 0)
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
                        val jpeg = image.use { toJpeg(it, maxSide, quality) }
                        val frameNo = next + 1
                        File(framesDir, "%06d.jpg".format(frameNo)).writeBytes(if (rotation == 0) jpeg else rotate(jpeg, rotation, quality))
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
            retriever.setDataSource(filePath)
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

        val y = yPlane.buffer
        for (row in 0 until height) {
            val source = (crop.top + row * k) * yPlane.rowStride + crop.left * yPlane.pixelStride
            val step = k * yPlane.pixelStride
            val target = row * width
            for (col in 0 until width) nv21[target + col] = y.get(source + col * step)
        }
        val u = uPlane.buffer
        val v = vPlane.buffer
        for (row in 0 until height / 2) {
            val chromaRow = crop.top / 2 + row * k
            val target = width * height + row * width
            for (col in 0 until width / 2) {
                val chromaCol = crop.left / 2 + col * k
                nv21[target + 2 * col] = v.get(chromaRow * vPlane.rowStride + chromaCol * vPlane.pixelStride)
                nv21[target + 2 * col + 1] = u.get(chromaRow * uPlane.rowStride + chromaCol * uPlane.pixelStride)
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
