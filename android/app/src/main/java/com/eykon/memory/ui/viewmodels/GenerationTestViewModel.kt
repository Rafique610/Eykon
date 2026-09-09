package com.eykon.memory.ui.viewmodels

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.eykon.memory.assistant.GenerationParams
import com.eykon.memory.assistant.GenerationResult
import com.eykon.memory.assistant.LiteRTGenerator
import com.eykon.memory.assistant.ModelManager
import com.eykon.memory.data.MemoryRecord
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class GenerationTestUiState(
    val modelStatus: ModelManager.ModelStatus,
    val cannedQuestion: String = "When is my dentist appointment?",
    val cannedMemories: List<MemoryRecord> = listOf(
        MemoryRecord(
            id = 1,
            text = "I have a dentist appointment with Dr. Smith next Tuesday at 3:00 PM.",
            timestamp = "2026-09-09T10:00:00"
        ),
        MemoryRecord(
            id = 2,
            text = "My brother's name is Ahmed.",
            timestamp = "2026-09-08T15:30:00"
        )
    ),
    val isGenerating: Boolean = false,
    val result: GenerationResult? = null,
    val generationParams: GenerationParams = GenerationParams()
)

class GenerationTestViewModel(application: Application) : AndroidViewModel(application) {

    private val generator = LiteRTGenerator(application)

    private val _uiState = MutableStateFlow(
        GenerationTestUiState(
            modelStatus = ModelManager.getModelStatus(application)
        )
    )
    val uiState: StateFlow<GenerationTestUiState> = _uiState.asStateFlow()

    fun refreshModelStatus() {
        _uiState.update {
            it.copy(modelStatus = ModelManager.getModelStatus(getApplication()))
        }
    }

    fun onQuestionChanged(newQuestion: String) {
        _uiState.update { it.copy(cannedQuestion = newQuestion) }
    }

    fun runGeneration() {
        val currentState = _uiState.value
        viewModelScope.launch {
            _uiState.update { it.copy(isGenerating = true, result = null) }
            val res = generator.generateAnswer(
                question = currentState.cannedQuestion,
                contextMemories = currentState.cannedMemories
            )
            _uiState.update {
                it.copy(
                    isGenerating = false,
                    result = res,
                    modelStatus = ModelManager.getModelStatus(getApplication())
                )
            }
        }
    }
}
