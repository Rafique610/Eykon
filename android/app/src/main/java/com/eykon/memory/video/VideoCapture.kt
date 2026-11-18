package com.eykon.memory.video

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.media.MediaMetadataRetriever
import android.net.Uri
import android.provider.MediaStore
import android.provider.OpenableColumns
import android.util.Log
import androidx.core.content.ContextCompat
import java.io.File
import java.io.InputStream
import java.time.Instant
import java.util.UUID

/**
 * What reading a video's recording place needs: the media-location permission and full video access. With only the picker's grant
 * the original file is refused (SecurityException "has no access to ...?requireOriginal=1"), checked on the Pixel, Android 17.
 */
val PLACE_PERMISSIONS: Array<String> = arrayOf(
    Manifest.permission.ACCESS_MEDIA_LOCATION,
    if (android.os.Build.VERSION.SDK_INT >= 33) Manifest.permission.READ_MEDIA_VIDEO else Manifest.permission.READ_EXTERNAL_STORAGE,
)

/** The picked file was refused; the message is safe to show to the person. */
class UploadException(message: String) : Exception(message)

/** [placeBlocked]: no place was read because the app may not read media locations (the user said no), so the screen can say so. */
data class SavedVideo(val video: Video, val timeFromFile: Boolean, val placeBlocked: Boolean = false)

/**
 * Phone twin of the laptop's capture.py: check, read metadata, add the videos row and its job.
 * EYKO-126: the picked gallery file is read in place (a kept read permission, no copy). Only when the phone will not
 * keep that permission is the file copied into app storage. The copy has no fixed size limit (EYKO-122: 500 MB was 1.5 to 4
 * minutes of phone video); it needs the video plus [VideoCopy.RESERVE_BYTES] free, checked before and during the copy.
 */
class VideoCapture(
    private val context: Context,
    private val repository: VideoRepository,
    private val jobs: VideoJobs,
) {

    /** A refusal is logged under the stage tag too, so a run's log counts refusals and not only the screen shows them. */
    fun save(uri: Uri): SavedVideo =
        try {
            saveChecked(uri)
        } catch (e: UploadException) {
            Log.i(TAG, "refused ${runCatching { nameOf(uri) }.getOrNull() ?: uri}: ${e.message}")
            throw e
        }

    private fun saveChecked(uri: Uri): SavedVideo {
        val ext = VideoMetadata.TYPES[context.contentResolver.getType(uri)]
            ?: throw UploadException("This file type is not supported. Use one of: ${VideoMetadata.TYPE_NAMES}.")
        val open = { context.contentResolver.openInputStream(uri) ?: throw UploadException("This file could not be opened.") }
        if (!keepReadPermission(uri)) return saveStream(ext, sizeOf(uri), open)

        // Nothing is copied, so only the frames, audio and database rows need room.
        VideoCopy.roomProblem(null, context.filesDir.usableSpace)?.let { throw UploadException(it) }
        refuseUnreadable(uri.toString()) // EYKO-118 B7/B10c: a damaged file is refused before it is read in full to hash it
        val videoId = newId()
        val folder = File(context.filesDir, "videos/$videoId").apply { mkdirs() }
        try {
            val read = VideoCopy.hashOnly(open())
            Log.i(TAG, "read $videoId: ${read.bytes} bytes in place in ${read.copyMs} ms (no copy)")
            // file_path names no file here: it only tells the stages where the video's folder is
            return register(videoId, File(folder, "$videoId.$ext"), read.sha256, uri.toString(), nameOf(uri))
        } catch (e: Exception) {
            folder.deleteRecursively()
            throw e
        }
    }

    /**
     * The copy path: everything after the file type is known. [sizeBytes] is the size the picker reports (null if it does not say).
     * Split from [save] so a test can hand in a stream without a content provider.
     */
    internal fun saveStream(ext: String, sizeBytes: Long?, open: () -> InputStream): SavedVideo {
        VideoCopy.roomProblem(sizeBytes, context.filesDir.usableSpace)?.let { throw UploadException(it) }

        val videoId = newId()
        val folder = File(context.filesDir, "videos/$videoId").apply { mkdirs() }
        val file = File(folder, "$videoId.$ext")
        try {
            val copied = VideoCopy.copyAndHash(open(), file, Long.MAX_VALUE) { context.filesDir.usableSpace }
            Log.i(TAG, "copy $videoId: ${copied.bytes} bytes in ${copied.copyMs} ms (hash ${copied.hashMs} ms)")
            return register(videoId, file, copied.sha256, sourceUri = null, displayName = null)
        } catch (e: Exception) {
            folder.deleteRecursively()
            throw e
        }
    }

    /** Refuse a duplicate, read the metadata from [sourceUri] (or the copy at [file]), then add the videos row and its job. */
    private fun register(videoId: String, file: File, sha256: String, sourceUri: String?, displayName: String?): SavedVideo {
        repository.findByHash(sha256)?.let {
            throw UploadException("This video is already saved (recorded ${it.recordedAt.take(10)}).")
        }
        val retriever = MediaMetadataRetriever()
        val video: Video
        val recorded: Instant?
        try {
            VideoSource.setOn(retriever, VideoSource.of(file.absolutePath, sourceUri))
            if (retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_HAS_VIDEO) != "yes") {
                throw UploadException(NOT_A_VIDEO)
            }
            recorded = VideoMetadata.parseRecordedAt(retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DATE))
            val place = VideoMetadata.parseLocation(retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_LOCATION))
                ?: sourceUri?.let { originalLocation(Uri.parse(it)) }
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
                contentHash = sha256,
                sourceUri = sourceUri,
                displayName = displayName,
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
        val placeBlocked = video.lat == null && sourceUri != null && !mayReadPlaces()
        return SavedVideo(video, timeFromFile = recorded != null, placeBlocked = placeBlocked)
    }

    private fun mayReadPlaces() = PLACE_PERMISSIONS.all {
        ContextCompat.checkSelfPermission(context, it) == PackageManager.PERMISSION_GRANTED
    }

    /** Throws [NOT_A_VIDEO] when the phone cannot read a video track from [source] (cheap: reads the header only). */
    private fun refuseUnreadable(source: String) {
        val retriever = MediaMetadataRetriever()
        try {
            VideoSource.setOn(retriever, source)
            if (retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_HAS_VIDEO) != "yes") throw UploadException(NOT_A_VIDEO)
        } catch (e: RuntimeException) {
            throw UploadException(NOT_A_VIDEO)
        } finally {
            retriever.release()
        }
    }

    /**
     * EYKO-127: Android removes the recording place from what it hands the app. With the media-location permission the original can be
     * read: the file picker's link is mapped to its media-store link and opened as the original. Any failure means "no place", never an error.
     */
    private fun originalLocation(uri: Uri): Pair<Double, Double>? {
        // Without the permission the original cannot be opened; MediaMetadataRetriever then only says "setDataSource failed"
        if (!mayReadPlaces()) {
            Log.i(TAG, "no original location for $uri: the app may not read media locations (permission denied)")
            return null
        }
        val retriever = MediaMetadataRetriever()
        return try {
            val media = MediaStore.getMediaUri(context, uri)
                ?: return null.also { Log.i(TAG, "no original location for $uri: no media-store entry for it") }
            // opened here, not by setDataSource(context, uri): that one swallows the real error and only says "setDataSource failed"
            val original = context.contentResolver.openFileDescriptor(MediaStore.setRequireOriginal(media), "r") ?: return null
            original.use { retriever.setDataSource(it.fileDescriptor) }
            val raw = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_LOCATION)
            VideoMetadata.parseLocation(raw).also { Log.i(TAG, "original location for $uri: '${raw.orEmpty()}' -> ${it ?: "none"}") }
        } catch (e: Exception) {
            Log.i(TAG, "no original location for $uri (${e.javaClass.simpleName}: ${e.message})")
            null
        } finally {
            retriever.release()
        }
    }

    /** Keeps the picker's read grant across restarts and reboots; false when the phone refuses (then the file is copied). */
    private fun keepReadPermission(uri: Uri): Boolean = try {
        context.contentResolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION)
        true
    } catch (e: SecurityException) {
        Log.w(TAG, "read permission for $uri cannot be kept (${e.message}); copying the file instead")
        false
    }

    private fun newId() = UUID.randomUUID().toString().replace("-", "")

    /** The size the picker reports for the file, or null when it does not say. */
    private fun sizeOf(uri: Uri): Long? = column(uri, OpenableColumns.SIZE) { cursor -> cursor.getLong(0).takeIf { it >= 0 } }

    /** The file's name as the gallery shows it, or null. */
    private fun nameOf(uri: Uri): String? = column(uri, OpenableColumns.DISPLAY_NAME) { cursor -> cursor.getString(0) }

    private fun <T> column(uri: Uri, name: String, read: (android.database.Cursor) -> T?): T? = try {
        context.contentResolver.query(uri, arrayOf(name), null, null, null)?.use { cursor ->
            if (cursor.moveToFirst() && !cursor.isNull(0)) read(cursor) else null
        }
    } catch (e: Exception) {
        null
    }

    private companion object {
        const val TAG = "EykonVideo"
        // EYKO-118: the same message covered damaged files (B7) and formats the phone cannot decode (B10c .avi); say both
        const val NOT_A_VIDEO = "This video is damaged or in a format this phone cannot read."
    }
}
