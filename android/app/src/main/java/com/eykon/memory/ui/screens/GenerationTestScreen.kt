package com.eykon.memory.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.eykon.memory.ui.viewmodels.GenerationTestViewModel

@Composable
fun GenerationTestScreen(
    viewModel: GenerationTestViewModel,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsState()
    var showPromptDetails by remember { mutableStateOf(false) }

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Column {
                Text(
                    text = "Gemma 4 Generation",
                    style = MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "Phase 2 Step 03 — On-Device LLM Test Harness",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }

        item {
            // Model Status Card
            val status = uiState.modelStatus
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = if (status.isAvailable)
                        MaterialTheme.colorScheme.primaryContainer
                    else
                        MaterialTheme.colorScheme.tertiaryContainer
                )
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = if (status.isAvailable) "🟢 Model Ready" else "⚠️ Model Sideload Pending",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                        OutlinedButton(
                            onClick = { viewModel.refreshModelStatus() }
                        ) {
                            Text("Refresh")
                        }
                    }
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = if (status.isAvailable)
                            "File found: ${status.filePath} (${status.sizeBytes / (1024 * 1024)} MB)"
                        else
                            "To sideload Gemma 4 E2B (~2.4 GB) to this device via ADB, run:\n\n${status.adbPushCommand}",
                        style = MaterialTheme.typography.bodySmall,
                        fontFamily = if (!status.isAvailable) FontFamily.Monospace else FontFamily.Default
                    )
                }
            }
        }

        item {
            // Generation Parameters Badge
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text(
                        text = "Generation Parameters (Phase 1 Parity)",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.SemiBold
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Temperature: ${uiState.generationParams.temperature} • Max Output Tokens: ${uiState.generationParams.maxOutputTokens} • TopK: ${uiState.generationParams.topK} • TopP: ${uiState.generationParams.topP}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }

        item {
            // Canned Context Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "Canned Test Context (2 Memories)",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    uiState.cannedMemories.forEachIndexed { i, mem ->
                        Text(
                            text = "[${i + 1}] ${mem.text}",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        if (i < uiState.cannedMemories.size - 1) {
                            Spacer(modifier = Modifier.height(4.dp))
                        }
                    }
                }
            }
        }

        item {
            // Question Input & Generate Button
            Column {
                OutlinedTextField(
                    value = uiState.cannedQuestion,
                    onValueChange = viewModel::onQuestionChanged,
                    label = { Text("Test Question") },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !uiState.isGenerating
                )
                Spacer(modifier = Modifier.height(12.dp))
                Button(
                    onClick = viewModel::runGeneration,
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !uiState.isGenerating
                ) {
                    if (uiState.isGenerating) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(20.dp),
                            strokeWidth = 2.dp,
                            color = MaterialTheme.colorScheme.onPrimary
                        )
                        Text("  Generating on-device...", modifier = Modifier.padding(start = 8.dp))
                    } else {
                        Text("🤖 Run Test Generation")
                    }
                }
            }
        }

        if (uiState.result != null) {
            val result = uiState.result!!
            item {
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
                                text = "Generated Answer",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = "⏱ ${result.latencyMs} ms",
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.primary
                            )
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = result.answer,
                            style = MaterialTheme.typography.bodyLarge,
                            fontWeight = FontWeight.Normal
                        )

                        Spacer(modifier = Modifier.height(12.dp))
                        HorizontalDivider()
                        Spacer(modifier = Modifier.height(8.dp))

                        OutlinedButton(
                            onClick = { showPromptDetails = !showPromptDetails },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(if (showPromptDetails) "Hide Full RAG Prompt" else "Inspect Full RAG Prompt")
                        }

                        AnimatedVisibility(visible = showPromptDetails) {
                            Column(modifier = Modifier.padding(top = 8.dp)) {
                                Text(
                                    text = result.fullPrompt,
                                    fontFamily = FontFamily.Monospace,
                                    fontSize = 11.sp,
                                    lineHeight = 15.sp,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
