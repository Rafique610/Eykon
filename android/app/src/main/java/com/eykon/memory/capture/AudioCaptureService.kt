package com.eykon.memory.capture

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.io.RandomAccessFile
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Service to capture 16kHz 16-bit Mono PCM audio via Android AudioRecord
 * and save as a standard RIFF/WAVE file for on-device speech-to-text processing.
 */
class AudioCaptureService {

    companion object {
        private const val TAG = "AudioCaptureService"
        const val SAMPLE_RATE = 16000
        const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
        const val BITS_PER_SAMPLE: Short = 16
        const val NUM_CHANNELS: Short = 1
        const val WAV_HEADER_SIZE = 44

        /**
         * Generates a standard 44-byte RIFF/WAVE header for 16-bit PCM audio.
         */
        fun buildWavHeader(
            audioDataLength: Long,
            sampleRate: Int = SAMPLE_RATE,
            numChannels: Short = NUM_CHANNELS,
            bitsPerSample: Short = BITS_PER_SAMPLE
        ): ByteArray {
            val byteRate = sampleRate * numChannels * (bitsPerSample / 8)
            val blockAlign = (numChannels * (bitsPerSample / 8)).toShort()
            val totalDataLen = audioDataLength + 36

            val buffer = ByteBuffer.allocate(WAV_HEADER_SIZE).order(ByteOrder.LITTLE_ENDIAN)
            buffer.put("RIFF".toByteArray())
            buffer.putInt(totalDataLen.toInt())
            buffer.put("WAVE".toByteArray())
            buffer.put("fmt ".toByteArray())
            buffer.putInt(16) // Subchunk1Size for PCM
            buffer.putShort(1) // AudioFormat 1 = PCM
            buffer.putShort(numChannels)
            buffer.putInt(sampleRate)
            buffer.putInt(byteRate)
            buffer.putShort(blockAlign)
            buffer.putShort(bitsPerSample)
            buffer.put("data".toByteArray())
            buffer.putInt(audioDataLength.toInt())

            return buffer.array()
        }
    }

    private var audioRecord: AudioRecord? = null
    private var recordingJob: Job? = null
    private var currentOutputFile: File? = null

    @Volatile
    var isRecording: Boolean = false
        private set

    /**
     * Starts recording audio into the specified target WAV file.
     */
    @SuppressLint("MissingPermission")
    fun startRecording(outputFile: File): Result<Unit> {
        if (isRecording) {
            return Result.failure(IllegalStateException("Recording is already in progress"))
        }

        val minBufferSize = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT)
        if (minBufferSize == AudioRecord.ERROR || minBufferSize == AudioRecord.ERROR_BAD_VALUE) {
            return Result.failure(IllegalStateException("AudioRecord minBufferSize error: $minBufferSize"))
        }

        val bufferSize = (minBufferSize * 2).coerceAtLeast(4096)

        return try {
            val record = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                bufferSize
            )

            if (record.state != AudioRecord.STATE_INITIALIZED) {
                record.release()
                return Result.failure(IllegalStateException("AudioRecord failed to initialize"))
            }

            record.startRecording()
            audioRecord = record
            currentOutputFile = outputFile
            isRecording = true

            recordingJob = CoroutineScope(Dispatchers.IO).launch {
                val outputStream = FileOutputStream(outputFile)
                // Write blank 44-byte header placeholder
                outputStream.write(ByteArray(WAV_HEADER_SIZE))

                val audioBuffer = ByteArray(bufferSize)
                var totalBytesRead = 0L

                try {
                    while (isActive && isRecording) {
                        val bytesRead = record.read(audioBuffer, 0, audioBuffer.size)
                        if (bytesRead > 0) {
                            outputStream.write(audioBuffer, 0, bytesRead)
                            totalBytesRead += bytesRead
                        }
                    }
                } finally {
                    outputStream.flush()
                    outputStream.close()

                    // Backfill valid WAV header with accurate byte count
                    if (outputFile.exists() && totalBytesRead > 0) {
                        RandomAccessFile(outputFile, "rw").use { raf ->
                            raf.seek(0)
                            raf.write(buildWavHeader(totalBytesRead))
                        }
                    }
                }
            }

            Result.success(Unit)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start recording: ${e.message}", e)
            cleanup()
            Result.failure(e)
        }
    }

    /**
     * Stops the active recording, finalizes the WAV file, and returns it.
     */
    suspend fun stopRecording(): Result<File> = withContext(Dispatchers.IO) {
        if (!isRecording) {
            return@withContext Result.failure(IllegalStateException("No active recording to stop"))
        }

        isRecording = false
        val file = currentOutputFile

        try {
            audioRecord?.stop()
        } catch (e: Exception) {
            Log.w(TAG, "AudioRecord stop warning: ${e.message}")
        }

        recordingJob?.join()
        cleanup()

        if (file != null && file.exists() && file.length() > WAV_HEADER_SIZE) {
            Result.success(file)
        } else {
            Result.failure(IllegalStateException("Recorded audio file is empty or missing"))
        }
    }

    /**
     * Cancels recording and deletes any partial output file.
     */
    fun cancelRecording() {
        isRecording = false
        try {
            audioRecord?.stop()
        } catch (e: Exception) {
            Log.w(TAG, "AudioRecord cancel warning: ${e.message}")
        }
        recordingJob?.cancel()
        currentOutputFile?.delete()
        cleanup()
    }

    private fun cleanup() {
        try {
            audioRecord?.release()
        } catch (e: Exception) {
            Log.w(TAG, "AudioRecord release warning: ${e.message}")
        }
        audioRecord = null
        recordingJob = null
        currentOutputFile = null
        isRecording = false
    }
}
