package com.eykon.memory.video

import java.io.File
import java.io.IOException
import java.io.InputStream
import java.security.MessageDigest

/** What a finished copy was: its size, its SHA-256, and how the time went (the hash time is part of the copy time). */
data class CopyResult(val bytes: Long, val sha256: String, val copyMs: Long, val hashMs: Long)

/**
 * EYKO-71. The file work of adding a video, with no Android classes so it runs in JVM tests:
 * copy the bytes, hash them on the way (no second read), and keep the phone from filling up.
 */
object VideoCopy {

    /** Free space that must be left after the copy: room for the frames and the database the stages write. */
    const val RESERVE_BYTES = 200L * 1024 * 1024

    private const val CHECK_EVERY_BYTES = 8L * 1024 * 1024

    /**
     * Why a file of [sizeBytes] (null when the picker does not say) should not be copied into [freeBytes], or null when it fits.
     * The copy is refused unless the video plus [RESERVE_BYTES] fits.
     */
    fun roomProblem(sizeBytes: Long?, freeBytes: Long): String? {
        val needed = (sizeBytes ?: 0L) + RESERVE_BYTES
        if (freeBytes >= needed) return null
        return if (sizeBytes != null) {
            "Not enough free space: this video needs about ${megabytes(needed)} MB (the video plus room to process it) and the phone has ${megabytes(freeBytes)} MB free. Free some space and try again."
        } else {
            "The phone is almost full (${megabytes(freeBytes)} MB free). Free some space and try again."
        }
    }

    /**
     * Copy [source] into [target] and return its SHA-256. The copy stops with an [UploadException] above [limitBytes], or when
     * [freeBytes] (checked every 8 MB) drops below the reserve. On any failure the half-written [target] is deleted.
     */
    fun copyAndHash(source: InputStream, target: File, limitBytes: Long, freeBytes: () -> Long): CopyResult {
        val digest = MessageDigest.getInstance("SHA-256")
        val buffer = ByteArray(1 shl 16)
        var total = 0L
        var sinceCheck = 0L
        var hashNs = 0L
        val start = System.nanoTime()
        try {
            source.use { input ->
                target.outputStream().use { sink ->
                    while (true) {
                        val read = input.read(buffer)
                        if (read < 0) break
                        total += read
                        if (total > limitBytes) throw UploadException(tooLarge(limitBytes))
                        val hashStart = System.nanoTime()
                        digest.update(buffer, 0, read)
                        hashNs += System.nanoTime() - hashStart
                        sink.write(buffer, 0, read)
                        sinceCheck += read
                        if (sinceCheck >= CHECK_EVERY_BYTES) {
                            sinceCheck = 0
                            roomProblem(null, freeBytes())?.let { throw UploadException(it) }
                        }
                    }
                }
            }
        } catch (e: Exception) {
            target.delete()
            if (e is IOException && (e.message ?: "").let { it.contains("ENOSPC") || it.contains("No space left", ignoreCase = true) }) {
                throw UploadException("The phone ran out of space while copying the video. Free some space and try again.")
            }
            throw e
        }
        return CopyResult(
            bytes = total,
            sha256 = digest.digest().joinToString("") { "%02x".format(it) },
            copyMs = (System.nanoTime() - start) / 1_000_000,
            hashMs = hashNs / 1_000_000,
        )
    }

    fun tooLarge(limitBytes: Long) = "This file is larger than the limit of ${limitBytes / (1024 * 1024)} MB."

    private fun megabytes(bytes: Long) = bytes / (1024 * 1024)
}
