package com.eykon.memory.assistant

import android.content.Context
import java.io.File

/**
 * Manages the on-device Gemma 4 LiteRT-LM model file location and status.
 */
object ModelManager {

    const val MODEL_FILENAME = "gemma-4-E2B-it.litertlm"
    private const val MIN_MODEL_SIZE_BYTES = 50 * 1024 * 1024L // Minimum 50 MB to prevent empty files

    data class ModelStatus(
        val isAvailable: Boolean,
        val filePath: String,
        val sizeBytes: Long,
        val targetDirectory: String,
        val adbPushCommand: String
    )

    fun getPreferredDirectory(context: Context): File {
        val externalDir = context.getExternalFilesDir(null)
        val modelsDir = File(externalDir ?: context.filesDir, "models")
        if (!modelsDir.exists()) {
            modelsDir.mkdirs()
        }
        return modelsDir
    }

    fun getModelStatus(context: Context): ModelStatus {
        val targetDir = getPreferredDirectory(context)
        val candidatePaths = listOf(
            File(targetDir, MODEL_FILENAME),
            File("/data/local/tmp", MODEL_FILENAME),
            File(File(context.filesDir, "models"), MODEL_FILENAME)
        )

        val foundFile = candidatePaths.firstOrNull { it.exists() && it.length() >= MIN_MODEL_SIZE_BYTES }

        val targetPath = File(targetDir, MODEL_FILENAME).absolutePath
        val isAvailable = foundFile != null
        val actualPath = foundFile?.absolutePath ?: targetPath
        val size = foundFile?.length() ?: 0L

        val adbCommand = "adb push \"models/$MODEL_FILENAME\" \"$targetPath\""

        return ModelStatus(
            isAvailable = isAvailable,
            filePath = actualPath,
            sizeBytes = size,
            targetDirectory = targetDir.absolutePath,
            adbPushCommand = adbCommand
        )
    }
}
