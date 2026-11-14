package com.eykon.memory.video

import android.media.MediaExtractor
import android.media.MediaMetadataRetriever
import android.net.Uri
import com.eykon.memory.MemoryApp
import java.io.FileNotFoundException

/**
 * EYKO-126: where a video's bytes are read from. Since this card the app reads the person's own gallery file
 * (`videos.source_uri`, a content:// link with a kept read permission) instead of a copy; videos added before it,
 * or when the permission could not be kept, still have their copy at `videos.file_path`.
 */
object VideoSource {

    /** The gallery link when there is one, otherwise the copy's path. */
    fun of(filePath: String, sourceUri: String?): String = sourceUri ?: filePath

    private fun isUri(source: String) = source.startsWith("content://")

    fun setOn(extractor: MediaExtractor, source: String) =
        if (isUri(source)) extractor.setDataSource(MemoryApp.instance, Uri.parse(source), null) else extractor.setDataSource(source)

    fun setOn(retriever: MediaMetadataRetriever, source: String) =
        if (isUri(source)) retriever.setDataSource(MemoryApp.instance, Uri.parse(source)) else retriever.setDataSource(source)

    /** Stops the job for good, with a clear message, when the gallery file was deleted or its permission is gone (retrying cannot help). */
    fun checkReadable(source: String) {
        if (!isUri(source)) return
        try {
            MemoryApp.instance.contentResolver.openFileDescriptor(Uri.parse(source), "r")?.close()
                ?: throw FileNotFoundException(source)
        } catch (e: Exception) {
            if (e is FileNotFoundException || e is SecurityException || e is IllegalArgumentException) {
                throw PermanentFailure("the original video was deleted from the phone or can no longer be read")
            }
            throw e
        }
    }
}
