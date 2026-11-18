package com.eykon.memory.video

import java.time.Instant
import java.time.LocalDateTime
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.time.format.DateTimeParseException

/** Pure parsers for what Android's MediaMetadataRetriever returns. No Android classes, so they run in JVM tests. */
object VideoMetadata {

    /**
     * Mime type -> file extension; the laptop accepts the same six (`src/config.py`). Android's supported-formats page lists
     * mp4, 3gp, mkv and webm; mov and m4v are mp4 by layout and work on our phones. avi was dropped: Android does not list it
     * and it failed on the Infinix and the Pixel (EYKO-118 B10c, EYKO-122).
     */
    val TYPES = mapOf(
        "video/mp4" to "mp4",
        "video/quicktime" to "mov",
        "video/x-m4v" to "m4v",
        "video/3gpp" to "3gp",
        "video/3gpp2" to "3gp",
        "video/x-matroska" to "mkv",
        "video/webm" to "webm",
    )

    /** The accepted extensions, for messages. */
    val TYPE_NAMES = TYPES.values.distinct().joinToString(", ")

    private val ISO6709 = Regex("""^([+-]\d+\.\d+)([+-]\d+\.\d+)""")
    private val RETRIEVER_DATE = DateTimeFormatter.ofPattern("yyyyMMdd'T'HHmmss[.SSS]'Z'")

    /** "+24.8607+067.0011/" -> (24.8607, 67.0011). */
    fun parseLocation(value: String?): Pair<Double, Double>? {
        val match = ISO6709.find(value?.trim() ?: return null) ?: return null
        return match.groupValues[1].toDouble() to match.groupValues[2].toDouble()
    }

    /**
     * "20261007T184200.000Z" -> that moment in UTC. Files with no recording time often report
     * 1 Jan 1904 (the container's zero date); anything before 1971 counts as "no time".
     */
    fun parseRecordedAt(value: String?): Instant? {
        val parsed = try {
            LocalDateTime.parse(value?.trim() ?: return null, RETRIEVER_DATE).toInstant(ZoneOffset.UTC)
        } catch (e: DateTimeParseException) {
            return null
        }
        return parsed.takeIf { it.isAfter(Instant.parse("1971-01-01T00:00:00Z")) }
    }
}
