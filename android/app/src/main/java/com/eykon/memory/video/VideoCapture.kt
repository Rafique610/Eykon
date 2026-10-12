package com.eykon.memory.video

import android.content.Context
import android.media.MediaMetadataRetriever
import android.net.Uri
import java.io.File
import java.time.Instant
import java.util.UUID

/** The picked file was refused; the message is safe to show to the person. */
class UploadException(message: String) : Exception(message)

data class SavedVideo(val video: Video, val timeFromFile: Boolean)

/** Phone twin of the laptop's capture.py: check, copy into app storage, read metadata, add the videos row. */
class VideoCapture(private val context: Context, private val repository: VideoRepository) {

    fun save(uri: Uri): SavedVideo {
        val ext = VideoMetadata.TYPES[context.contentResolver.getType(uri)]
            ?: throw UploadException("This file type is not supported. Use one of: mp4, mov, m4v, avi.")

        val videoId = UUID.randomUUID().toString().replace("-", "")
        val folder = File(context.filesDir, "videos/$videoId").apply { mkdirs() }
        val file = File(folder, "$videoId.$ext")
        try {
            copy(uri, file)
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
                )
            } catch (e: RuntimeException) {
                // setDataSource throws on files it cannot read at all
                throw UploadException(NOT_A_VIDEO)
            } finally {
                retriever.release()
            }
            repository.insert(video)
            return SavedVideo(video, timeFromFile = recorded != null)
        } catch (e: Exception) {
            folder.deleteRecursively()
            throw e
        }
    }

    private fun copy(uri: Uri, target: File) {
        val limit = VideoMetadata.MAX_MB * 1024L * 1024L
        val input = context.contentResolver.openInputStream(uri)
            ?: throw UploadException("This file could not be opened.")
        input.use { source ->
            target.outputStream().use { sink ->
                val buffer = ByteArray(1 shl 16)
                var total = 0L
                while (true) {
                    val read = source.read(buffer)
                    if (read < 0) break
                    total += read
                    if (total > limit) throw UploadException("This file is larger than the limit of ${VideoMetadata.MAX_MB} MB.")
                    sink.write(buffer, 0, read)
                }
            }
        }
    }

    private companion object {
        const val NOT_A_VIDEO = "This file does not contain a video that can be read."
    }
}
