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
import com.eykon.memory.video.Video
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

private val WHEN = DateTimeFormatter.ofPattern("d MMM yyyy, HH:mm", Locale.ENGLISH)

private fun localTime(isoUtc: String): String =
    WHEN.format(Instant.parse(isoUtc).atZone(ZoneId.systemDefault()))

/** The stored status in plain words. Nothing processes videos yet, so 'processing' means saved and waiting. */
private fun statusLabel(status: String): String = when (status) {
    "processing" -> "Saved, waiting to be processed"
    "ready" -> "Ready to search"
    "failed" -> "Processing failed"
    else -> status
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
        items(uiState.videos, key = { it.videoId }) { video ->
            VideoRow(video)
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
private fun VideoRow(video: Video) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(localTime(video.recordedAt), fontWeight = FontWeight.SemiBold)
            Text(
                String.format(Locale.ENGLISH, "%.0f s · %s", video.durationS, statusLabel(video.status)),
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}
