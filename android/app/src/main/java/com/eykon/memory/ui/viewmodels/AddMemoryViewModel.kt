package com.eykon.memory.ui.viewmodels

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.eykon.memory.capture.AudioCaptureService
import com.eykon.memory.capture.NativeSpeechRecognizer
import com.eykon.memory.capture.TextCaptureService
import com.eykon.memory.capture.WhisperTranscriber
import com.eykon.memory.data.MemoryDao
import com.eykon.memory.data.MemoryRecord
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.io.File

data class AddMemoryUiState(
    val inputText: String = "",
    val savedMessage: String? = null,
    val errorMessage: String? = null,
    val isSaving: Boolean = false,
    val isRecording: Boolean = false,
    val isTranscribing: Boolean = false,
    val currentSourceType: String = "text"
)

class AddMemoryViewModel(
    private val dao: MemoryDao,
    private val audioCaptureService: AudioCaptureService = AudioCaptureService(),
    private val whisperTranscriber: WhisperTranscriber? = null,
    private val speechRecognizer: NativeSpeechRecognizer? = null,
    private val cacheDirProvider: (() -> File)? = null
) : ViewModel() {

    private val _uiState = MutableStateFlow(AddMemoryUiState())
    val uiState: StateFlow<AddMemoryUiState> = _uiState.asStateFlow()

    // Real-time reactive flow of memories from Room SQLite
    val memories: StateFlow<List<MemoryRecord>> = dao.getAllAsFlow()
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = emptyList()
        )

    fun onInputTextChanged(newText: String) {
        _uiState.update {
            it.copy(
                inputText = newText,
                errorMessage = null,
                savedMessage = null
            )
        }
    }

    fun onSpeechResult(spokenText: String) {
        _uiState.update {
            it.copy(
                inputText = spokenText,
                currentSourceType = "audio",
                errorMessage = null,
                savedMessage = "Voice transcribed! You can review or edit before saving."
            )
        }
    }

    fun onSpeechError(error: String) {
        _uiState.update {
            it.copy(
                errorMessage = error
            )
        }
    }

    fun startAudioRecording() {
        if (speechRecognizer != null) {
            _uiState.update {
                it.copy(
                    isRecording = true,
                    errorMessage = null,
                    savedMessage = "Listening... Speak clearly into your phone."
                )
            }
            speechRecognizer.startListening(
                onPartialResult = { partial ->
                    _uiState.update {
                        it.copy(
                            inputText = partial,
                            currentSourceType = "audio"
                        )
                    }
                },
                onFinalResult = { text ->
                    _uiState.update {
                        it.copy(
                            inputText = text,
                            currentSourceType = "audio",
                            isRecording = false,
                            savedMessage = "Voice transcribed! Review or edit before saving."
                        )
                    }
                },
                onError = { err ->
                    _uiState.update {
                        it.copy(
                            isRecording = false,
                            errorMessage = err
                        )
                    }
                }
            )
            return
        }

        val cacheDir = cacheDirProvider?.invoke()
        val tempWavFile = if (cacheDir != null) {
            File(cacheDir, "temp_voice_record_${System.currentTimeMillis()}.wav")
        } else {
            File.createTempFile("temp_voice_record", ".wav")
        }

        val result = audioCaptureService.startRecording(tempWavFile)
        result.onSuccess {
            _uiState.update {
                it.copy(
                    isRecording = true,
                    errorMessage = null,
                    savedMessage = "Recording audio... Tap stop when finished."
                )
            }
        }.onFailure { e ->
            _uiState.update {
                it.copy(
                    isRecording = false,
                    errorMessage = "Failed to start recording: ${e.message}"
                )
            }
        }
    }

    fun stopAudioRecording() {
        if (speechRecognizer != null && speechRecognizer.isListening) {
            speechRecognizer.stopListening()
            _uiState.update { it.copy(isRecording = false) }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(isRecording = false, isTranscribing = true) }

            val stopResult = audioCaptureService.stopRecording()
            stopResult.onSuccess { recordedFile ->
                val transcriber = whisperTranscriber
                if (transcriber != null) {
                    val transcribeResult = transcriber.transcribe(recordedFile)
                    transcribeResult.onSuccess { transcript ->
                        _uiState.update {
                            it.copy(
                                inputText = transcript,
                                currentSourceType = "audio",
                                savedMessage = "Audio transcribed! You can review or edit before saving.",
                                isTranscribing = false
                            )
                        }
                    }.onFailure { e ->
                        _uiState.update {
                            it.copy(
                                errorMessage = "Transcription failed: ${e.message}",
                                isTranscribing = false
                            )
                        }
                    }
                } else {
                    _uiState.update {
                        it.copy(
                            inputText = "Voice note recorded (${recordedFile.length()} bytes)",
                            currentSourceType = "audio",
                            savedMessage = "Audio captured.",
                            isTranscribing = false
                        )
                    }
                }

                // Discard raw audio after transcription (Decision #2 in Step 05 Plan)
                try {
                    recordedFile.delete()
                } catch (_: Exception) {}
            }.onFailure { e ->
                _uiState.update {
                    it.copy(
                        isTranscribing = false,
                        errorMessage = "Audio capture error: ${e.message}"
                    )
                }
            }
        }
    }

    fun onPermissionDenied() {
        _uiState.update {
            it.copy(
                errorMessage = "Microphone permission is required to capture voice memories."
            )
        }
    }

    fun saveMemory() {
        val currentText = _uiState.value.inputText
        val currentSource = _uiState.value.currentSourceType

        viewModelScope.launch {
            try {
                _uiState.update { it.copy(isSaving = true, errorMessage = null) }
                val records = TextCaptureService.createMemoriesFromText(
                    text = currentText,
                    sourceType = currentSource
                )
                val ids = dao.insertAll(records)

                _uiState.update {
                    it.copy(
                        inputText = "",
                        currentSourceType = "text",
                        savedMessage = "Memory saved! (IDs: ${ids.joinToString()})",
                        errorMessage = null,
                        isSaving = false
                    )
                }
            } catch (e: IllegalArgumentException) {
                _uiState.update {
                    it.copy(
                        errorMessage = e.message ?: "Invalid memory text",
                        savedMessage = null,
                        isSaving = false
                    )
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        errorMessage = "Storage error: ${e.localizedMessage}",
                        savedMessage = null,
                        isSaving = false
                    )
                }
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        speechRecognizer?.destroy()
    }

    companion object {
        fun provideFactory(dao: MemoryDao, context: Context? = null): ViewModelProvider.Factory =
            object : ViewModelProvider.Factory {
                @Suppress("UNCHECKED_CAST")
                override fun <T : ViewModel> create(modelClass: Class<T>): T {
                    if (modelClass.isAssignableFrom(AddMemoryViewModel::class.java)) {
                        val transcriber = context?.let { WhisperTranscriber(it.applicationContext) }
                        val recognizer = context?.let { NativeSpeechRecognizer(it) }
                        val cacheProvider = context?.let { { it.applicationContext.cacheDir } }
                        return AddMemoryViewModel(
                            dao = dao,
                            whisperTranscriber = transcriber,
                            speechRecognizer = recognizer,
                            cacheDirProvider = cacheProvider
                        ) as T
                    }
                    throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
                }
            }
    }
}
