package com.eykon.memory.ui.screens

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import android.graphics.BitmapFactory
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import com.eykon.memory.ui.viewmodels.VideoViewModel
import com.eykon.memory.video.FrameHit
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
        "failed" -> "Failed at stage ${done + 1} of ${stages.size} (${stages.getOrElse(done) { "?" }}) after ${item.jobAttempts} attempts: ${item.jobError.orEmpty()}"
        "done" -> when {
            item.video.status == "ready" -> "Ready to search"
            stages.isEmpty() -> "Job finished (no processing stages exist yet)"
            else -> "Job finished ($done of ${stages.size} stages)"
        }
        else -> item.jobStatus
    }
}

private fun count(n: Int, thing: String) = if (n == 1) "1 $thing" else "$n ${thing}s"

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
        uiState.readyNotice?.let { notice ->
            item { MessageCard(notice, MaterialTheme.colorScheme.primaryContainer) }
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
            Text("Find a moment", style = MaterialTheme.typography.titleMedium)
            OutlinedTextField(
                value = uiState.query,
                onValueChange = viewModel::onQueryChanged,
                label = { Text("What to look for, for example: a helmet") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                keyboardActions = KeyboardActions(onSearch = { viewModel.onSearch() }),
                modifier = Modifier.fillMaxWidth(),
            )
            Button(
                onClick = viewModel::onSearch,
                enabled = uiState.query.isNotBlank() && !uiState.isSearching,
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
            ) {
                Text(if (uiState.isSearching) "Searching…" else "Search frames")
            }
        }
        uiState.searchError?.let { message ->
            item { MessageCard(message, MaterialTheme.colorScheme.errorContainer) }
        }
        uiState.hits?.let { hits ->
            item {
                Text(
                    if (hits.isEmpty()) "No frames are stored yet. Add a video and wait for it to finish."
                    else "Closest ${hits.size} frames for \"${uiState.searchedFor}\" (${uiState.searchMs} ms), best first",
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            items(hits, key = { "hit-${it.frameId}" }) { hit -> HitRow(hit) }
        }
        item {
            Text(
                if (uiState.videos.isEmpty()) "No videos yet." else "Saved videos (${uiState.videos.size})",
                style = MaterialTheme.typography.titleMedium,
            )
        }
        items(uiState.videos, key = { it.video.videoId }) { item ->
            VideoRow(item, onRetry = viewModel::onRetry)
        }
    }
}

@Composable
private fun MessageCard(text: String, color: androidx.compose.ui.graphics.Color) {
    Card(colors = CardDefaults.cardColors(containerColor = color), modifier = Modifier.fillMaxWidth()) {
        Text(text, modifier = Modifier.padding(12.dp))
    }
}

/** One found frame: the picture, when it was, how alike it is to the phrase, and its stored caption. */
@Composable
private fun HitRow(hit: FrameHit) {
    val picture = remember(hit.file) { BitmapFactory.decodeFile(hit.file.absolutePath)?.asImageBitmap() }
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp)) {
            if (picture != null) {
                Image(picture, contentDescription = hit.caption ?: "Video frame", contentScale = ContentScale.Fit, modifier = Modifier.fillMaxWidth().height(220.dp))
            }
            Text(
                String.format(Locale.ENGLISH, "%s · at %.1f s · likeness %.3f", localTime(hit.recordedAt), hit.tS, hit.score),
                fontWeight = FontWeight.SemiBold,
            )
            hit.caption?.let { Text("Stored caption: $it", style = MaterialTheme.typography.bodySmall) }
        }
    }
}

@Composable
private fun VideoRow(item: VideoWithJob, onRetry: (Long) -> Unit) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(localTime(item.video.recordedAt), fontWeight = FontWeight.SemiBold)
            Text(
                String.format(Locale.ENGLISH, "%.0f s · %s", item.video.durationS, statusLabel(item)),
                style = MaterialTheme.typography.bodySmall,
            )
            Text(
                "${count(item.keptFrames, "frame")} kept · ${count(item.speechSegments, "speech segment")} · ${count(item.transcriptChunks, "transcript chunk")}",
                style = MaterialTheme.typography.bodySmall,
            )
            if (item.jobStatus == "failed" && item.jobId != null) {
                Button(onClick = { onRetry(item.jobId) }, modifier = Modifier.padding(top = 8.dp)) { Text("Retry") }
            }
        }
    }
}
