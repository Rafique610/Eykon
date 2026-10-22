package com.eykon.memory.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import com.eykon.memory.assistant.ModelManager
import com.eykon.memory.data.MemoryRecord
import com.eykon.memory.ui.components.MemoryHeaderBar
import com.eykon.memory.ui.components.VoiceRecordButton
import com.eykon.memory.ui.viewmodels.AddMemoryViewModel

@Composable
fun AddMemoryScreen(
    viewModel: AddMemoryViewModel,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsState()
    val memories by viewModel.memories.collectAsState()
    val context = LocalContext.current
    val isModelReady = remember { ModelManager.getModelStatus(context).isAvailable }

    Column(modifier = modifier.fillMaxSize()) {
        MemoryHeaderBar(
            memoryCount = memories.size,
            isModelReady = isModelReady
        )

        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {

        item {
            CaptureInputCard(
                inputText = uiState.inputText,
                isSaving = uiState.isSaving,
                isRecording = uiState.isRecording,
                isTranscribing = uiState.isTranscribing,
                currentSourceType = uiState.currentSourceType,
                onTextChanged = viewModel::onInputTextChanged,
                onSave = viewModel::saveMemory,
                onSpeechResult = viewModel::onSpeechResult,
                onError = viewModel::onSpeechError,
                onPermissionDenied = viewModel::onPermissionDenied
            )
        }

        if (uiState.savedMessage != null) {
            item {
                StatusBanner(
                    message = uiState.savedMessage!!,
                    isError = false
                )
            }
        }

        if (uiState.errorMessage != null) {
            item {
                StatusBanner(
                    message = uiState.errorMessage!!,
                    isError = true
                )
            }
        }

        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Recent Memories",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "Total: ${memories.size}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.primary
                )
            }
        }

        if (memories.isEmpty()) {
            item {
                Text(
                    text = "No memories stored yet. Type or record a memory above to test on-device SQLite storage.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        } else {
            items(memories.take(10), key = { it.id }) { memory ->
                MemoryItemCard(memory = memory)
            }
        }
    }
}
}

@Composable
private fun CaptureInputCard(
    inputText: String,
    isSaving: Boolean,
    isRecording: Boolean,
    isTranscribing: Boolean,
    currentSourceType: String,
    onTextChanged: (String) -> Unit,
    onSave: () -> Unit,
    onSpeechResult: (String) -> Unit,
    onError: (String) -> Unit,
    onPermissionDenied: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Capture Memory",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold
                )

                if (currentSourceType == "audio") {
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(8.dp))
                            .background(MaterialTheme.colorScheme.tertiaryContainer)
                            .padding(horizontal = 8.dp, vertical = 4.dp)
                    ) {
                        Text(
                            text = "🎤 Voice",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onTertiaryContainer,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            OutlinedTextField(
                value = inputText,
                onValueChange = onTextChanged,
                label = { Text("Type or record memory...") },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(130.dp),
                maxLines = 5,
                enabled = !isSaving
            )

            Spacer(modifier = Modifier.height(12.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                VoiceRecordButton(
                    isRecording = isRecording,
                    isTranscribing = isTranscribing,
                    onSpeechResult = onSpeechResult,
                    onError = onError,
                    onPermissionDenied = onPermissionDenied,
                    modifier = Modifier.weight(1f)
                )

                Button(
                    onClick = onSave,
                    modifier = Modifier.weight(1f),
                    enabled = !isSaving && !isRecording && !isTranscribing && inputText.isNotBlank()
                ) {
                    if (isSaving) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(18.dp),
                            strokeWidth = 2.dp,
                            color = MaterialTheme.colorScheme.onPrimary
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Saving...")
                    } else {
                        Text("Save Memory")
                    }
                }
            }
        }
    }
}

@Composable
private fun StatusBanner(message: String, isError: Boolean) {
    val containerColor = if (isError) {
        MaterialTheme.colorScheme.errorContainer
    } else {
        MaterialTheme.colorScheme.primaryContainer
    }
    val contentColor = if (isError) {
        MaterialTheme.colorScheme.onErrorContainer
    } else {
        MaterialTheme.colorScheme.onPrimaryContainer
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = containerColor)
    ) {
        Text(
            text = message,
            color = contentColor,
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.padding(12.dp),
            fontWeight = FontWeight.Medium
        )
    }
}

@Composable
private fun MemoryItemCard(memory: MemoryRecord) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(
                text = memory.text,
                style = MaterialTheme.typography.bodyLarge
            )
            Spacer(modifier = Modifier.height(6.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                val icon = when (memory.sourceType) {
                    "audio" -> "🎤 audio"
                    "video" -> "📹 video"
                    else -> "📝 text"
                }
                Text(
                    text = "ID: #${memory.id} • $icon",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = memory.timestamp.take(19).replace('T', ' '),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}
