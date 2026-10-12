package com.eykon.memory.ui.screens

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.eykon.memory.ui.viewmodels.VideoViewModel
import com.eykon.memory.video.SavedVideo
import com.eykon.memory.video.VideoPipeline
import com.eykon.memory.video.VideoWithJob
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

private val WHEN = DateTimeFormatter.ofPattern("d MMM yyyy, HH:mm", Locale.ENGLISH)

private fun localTime(isoUtc: String): String =
    WHEN.format(Instant.parse(isoUtc).atZone(ZoneId.systemDefault()))

/** Where the video's job stands, in plain words, from the stored job row. */
private fun statusLabel(item: VideoWithJob): String {
    val stages = VideoPipeline.STAGES.map { it.first }
    val done = stages.indexOf(item.jobStage) + 1 // 0 when no stage has finished
    return when (item.jobStatus) {
        null -> "Saved, no job (added before the queue existed)"
        "queued" -> if (item.jobAttempts > 0) "Waiting to retry (attempt ${item.jobAttempts + 1})" else "Waiting in the queue"
        "running" -> "Processing: stage ${done + 1} of ${stages.size}"
        "failed" -> "Failed after ${item.jobAttempts} attempts: ${item.jobError.orEmpty()}"
        "done" -> when {
            item.video.status == "ready" -> "Ready to search"
            stages.isEmpty() -> "Job finished (no processing stages exist yet)"
            else -> "Job finished ($done of ${stages.size} stages)"
        }
        else -> item.jobStatus
    }
}

private fun confirmation(saved: SavedVideo): String {
    val video = saved.video
    val time = if (saved.timeFromFile) {
        "Recorded ${localTime(video.recordedAt)}"
    } else {
        "Added ${localTime(video.recordedAt)} (the file carries no recording time)"
    }
    val place = if (video.lat != null && video.lon != null) {
        String.format(Locale.ENGLISH, ", at %.4f, %.4f", video.lat, video.lon)
    } else ""
    return String.format(Locale.ENGLISH, "Saved. %s, %.0f s%s.", time, video.durationS, place)
}

@Composable
fun VideoScreen(
    viewModel: VideoViewModel,
    modifier: Modifier = Modifier,
) {
    val uiState by viewModel.uiState.collectAsState()
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        viewModel.onVideoPicked(uri)
    }

    LazyColumn(
        modifier = modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Text("Video memory", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            Text(
                "Add a recorded clip. It is stored on this phone and nothing is sent anywhere.",
                style = MaterialTheme.typography.bodyMedium,
            )
        }
        item {
            Button(
                onClick = { picker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.VideoOnly)) },
                enabled = !uiState.isSaving,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(if (uiState.isSaving) "Saving…" else "Add a video")
            }
        }
        if (uiState.isSaving) {
            item { CircularProgressIndicator() }
        }
        uiState.saved?.let { saved ->
            item {
                MessageCard(confirmation(saved), MaterialTheme.colorScheme.primaryContainer)
            }
        }
        uiState.errorMessage?.let { message ->
            item {
                MessageCard(message, MaterialTheme.colorScheme.errorContainer)
            }
        }
        item {
            Text(
                if (uiState.videos.isEmpty()) "No videos yet." else "Saved videos (${uiState.videos.size})",
                style = MaterialTheme.typography.titleMedium,
            )
        }
        items(uiState.videos, key = { it.video.videoId }) { item ->
            VideoRow(item)
        }
    }
}

@Composable
private fun MessageCard(text: String, color: androidx.compose.ui.graphics.Color) {
    Card(colors = CardDefaults.cardColors(containerColor = color), modifier = Modifier.fillMaxWidth()) {
        Text(text, modifier = Modifier.padding(12.dp))
    }
}

@Composable
private fun VideoRow(item: VideoWithJob) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(localTime(item.video.recordedAt), fontWeight = FontWeight.SemiBold)
            Text(
                String.format(Locale.ENGLISH, "%.0f s · %s", item.video.durationS, statusLabel(item)),
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}
