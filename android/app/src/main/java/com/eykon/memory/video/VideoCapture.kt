package com.eykon.memory.video

import android.content.Context
import android.media.MediaMetadataRetriever
import android.net.Uri
import android.provider.OpenableColumns
import android.util.Log
import java.io.File
import java.io.InputStream
import java.time.Instant
import java.util.UUID

/** The picked file was refused; the message is safe to show to the person. */
class UploadException(message: String) : Exception(message)

data class SavedVideo(val video: Video, val timeFromFile: Boolean)

/** Phone twin of the laptop's capture.py: check, copy into app storage, read metadata, add the videos row and its job. */
class VideoCapture(
    private val context: Context,
    private val repository: VideoRepository,
    private val jobs: VideoJobs,
) {

    fun save(uri: Uri): SavedVideo {
        val ext = VideoMetadata.TYPES[context.contentResolver.getType(uri)]
            ?: throw UploadException("This file type is not supported. Use one of: mp4, mov, m4v, avi.")
        return saveStream(ext, sizeOf(uri)) {
            context.contentResolver.openInputStream(uri) ?: throw UploadException("This file could not be opened.")
        }
    }

    /**
     * Everything after the file type is known. [sizeBytes] is the size the picker reports (null if it does not say).
     * Split from [save] so a test can hand in a stream without a content provider.
     */
    internal fun saveStream(ext: String, sizeBytes: Long?, open: () -> InputStream): SavedVideo {
        val limit = VideoMetadata.MAX_MB * 1024L * 1024L
        if (sizeBytes != null && sizeBytes > limit) throw UploadException(VideoCopy.tooLarge(limit))
        VideoCopy.roomProblem(sizeBytes, context.filesDir.usableSpace)?.let { throw UploadException(it) }

        val videoId = UUID.randomUUID().toString().replace("-", "")
        val folder = File(context.filesDir, "videos/$videoId").apply { mkdirs() }
        val file = File(folder, "$videoId.$ext")
        try {
            val copied = VideoCopy.copyAndHash(open(), file, limit) { context.filesDir.usableSpace }
            Log.i(TAG, "copy $videoId: ${copied.bytes} bytes in ${copied.copyMs} ms (hash ${copied.hashMs} ms)")
            repository.findByHash(copied.sha256)?.let {
                throw UploadException("This video is already saved (recorded ${it.recordedAt.take(10)}).")
            }
            val retriever = MediaMetadataRetriever()
            val video: Video
            val recorded: Instant?
            try {
                retriever.setDataSource(file.absolutePath)
                if (retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_HAS_VIDEO) != "yes") {
                    throw UploadException(NOT_A_VIDEO)
                }
                recorded = VideoMetadata.parseRecordedAt(retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DATE))
                val place = VideoMetadata.parseLocation(retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_LOCATION))
                val durationMs = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLongOrNull() ?: 0L
                val now = Instant.now()
                video = Video(
                    videoId = videoId,
                    filePath = file.absolutePath,
                    recordedAt = (recorded ?: now).toString(),
                    createdAt = now.toString(),
                    durationS = durationMs / 1000.0,
                    lat = place?.first,
                    lon = place?.second,
                    contentHash = copied.sha256,
                )
            } catch (e: RuntimeException) {
                // setDataSource throws on files it cannot read at all
                throw UploadException(NOT_A_VIDEO)
            } finally {
                retriever.release()
            }
            repository.transaction {
                repository.insert(video)
                jobs.enqueue(video.videoId)
            }
            return SavedVideo(video, timeFromFile = recorded != null)
        } catch (e: Exception) {
            folder.deleteRecursively()
            throw e
        }
    }

    /** The size the picker reports for the file, or null when it does not say. */
    private fun sizeOf(uri: Uri): Long? = try {
        context.contentResolver.query(uri, arrayOf(OpenableColumns.SIZE), null, null, null)?.use { cursor ->
            if (cursor.moveToFirst() && !cursor.isNull(0)) cursor.getLong(0).takeIf { it >= 0 } else null
        }
    } catch (e: Exception) {
        null
    }

    private companion object {
        const val TAG = "EykonVideo"
        const val NOT_A_VIDEO = "This file does not contain a video that can be read."
    }
}
