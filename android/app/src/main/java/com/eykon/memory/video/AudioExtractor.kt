package com.eykon.memory.video

import android.media.AudioFormat
import android.media.MediaCodec
import android.media.MediaExtractor
import android.media.MediaFormat
import com.eykon.memory.capture.AudioCaptureService
import java.io.File
import java.io.RandomAccessFile
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** Turns a video's sound track into a 16-bit mono WAV at a given rate. */
object AudioExtractor {

    /** Writes the WAV and returns how many samples it holds. A video with no sound gets silence of its length. */
    fun toWav(filePath: String, wav: File, durationS: Double, rate: Int): Long {
        var samples = 0L
        RandomAccessFile(wav, "rw").use { file ->
            file.setLength(0)
            file.write(ByteArray(AudioCaptureService.WAV_HEADER_SIZE))
            val chunk = ByteBuffer.allocate(16_384).order(ByteOrder.LITTLE_ENDIAN)
            val emit: (Short) -> Unit = { sample ->
                if (!chunk.hasRemaining()) {
                    file.write(chunk.array(), 0, chunk.position())
                    chunk.clear()
                }
                chunk.putShort(sample)
                samples++
            }
            if (!decode(filePath, rate, emit)) {
                repeat((durationS * rate).toInt()) { emit(0) }
            }
            file.write(chunk.array(), 0, chunk.position())
            file.seek(0)
            file.write(AudioCaptureService.buildWavHeader(samples * 2, rate))
        }
        return samples
    }

    /** Decodes the first audio track to mono at [rate]. False when the video has no audio track. */
    private fun decode(filePath: String, rate: Int, emit: (Short) -> Unit): Boolean {
        val extractor = MediaExtractor()
        try {
            extractor.setDataSource(filePath)
            val track = (0 until extractor.trackCount).firstOrNull {
                extractor.getTrackFormat(it).getString(MediaFormat.KEY_MIME)?.startsWith("audio/") == true
            } ?: return false
            val format = extractor.getTrackFormat(track)
            extractor.selectTrack(track)

            val codec = MediaCodec.createDecoderByType(format.getString(MediaFormat.KEY_MIME)!!)
            try {
                codec.configure(format, null, null, 0)
                codec.start()
                var inRate = format.getInteger(MediaFormat.KEY_SAMPLE_RATE)
                var channels = format.getInteger(MediaFormat.KEY_CHANNEL_COUNT)
                var isFloat = false
                var resampler: MonoResampler? = null
                val info = MediaCodec.BufferInfo()
                var inputDone = false
                var outputDone = false
                while (!outputDone) {
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
                    if (outIndex == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                        val out = codec.outputFormat
                        inRate = out.getInteger(MediaFormat.KEY_SAMPLE_RATE)
                        channels = out.getInteger(MediaFormat.KEY_CHANNEL_COUNT)
                        isFloat = out.containsKey(MediaFormat.KEY_PCM_ENCODING) &&
                            out.getInteger(MediaFormat.KEY_PCM_ENCODING) == AudioFormat.ENCODING_PCM_FLOAT
                        resampler = null
                    } else if (outIndex >= 0) {
                        if (info.size > 0) {
                            val buffer = codec.getOutputBuffer(outIndex)!!
                            buffer.position(info.offset).limit(info.offset + info.size)
                            buffer.order(ByteOrder.nativeOrder())
                            val pcm = if (isFloat) {
                                val floats = buffer.asFloatBuffer()
                                ShortArray(floats.remaining()) { (floats.get().coerceIn(-1f, 1f) * 32767f).toInt().toShort() }
                            } else {
                                val shorts = buffer.asShortBuffer()
                                ShortArray(shorts.remaining()).also { shorts.get(it) }
                            }
                            val active = resampler ?: MonoResampler(inRate, channels, rate).also { resampler = it }
                            active.feed(pcm, pcm.size, emit)
                        }
                        codec.releaseOutputBuffer(outIndex, false)
                        if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) outputDone = true
                    }
                }
            } finally {
                codec.stop()
                codec.release()
            }
            return true
        } finally {
            extractor.release()
        }
    }
}
