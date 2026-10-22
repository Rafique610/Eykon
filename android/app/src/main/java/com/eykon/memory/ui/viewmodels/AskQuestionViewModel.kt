package com.eykon.memory.ui.viewmodels

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.eykon.memory.assistant.GenerationResult
import com.eykon.memory.assistant.LiteRTGenerator
import com.eykon.memory.assistant.ModelManager
import com.eykon.memory.data.MemoryDao
import com.eykon.memory.data.MemoryRecord
import com.eykon.memory.retrieval.SearchService
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

data class AskQuestionUiState(
    val query: String = "",
    val isSearching: Boolean = false,
    val isGenerating: Boolean = false,
    val loadingMessage: String = "",
    val answer: String? = null,
    val retrievedMemories: List<Pair<MemoryRecord, Float>> = emptyList(),
    val latencyMs: Long = 0L,
    val errorMessage: String? = null,
    val modelStatus: ModelManager.ModelStatus,
    val memoryCount: Int = 0
) {
    val isLoading: Boolean
        get() = isSearching || isGenerating
}

class AskQuestionViewModel(
    private val dao: MemoryDao,
    private val searchService: SearchService,
    private val generator: LiteRTGenerator? = null,
    private val modelStatusProvider: () -> ModelManager.ModelStatus = {
        ModelManager.ModelStatus(
            isAvailable = false,
            filePath = "",
            sizeBytes = 0L,
            targetDirectory = "",
            adbPushCommand = ""
        )
    },
    private val answerGenerator: (suspend (String, List<MemoryRecord>) -> GenerationResult)? = null,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO,
    private val defaultDispatcher: CoroutineDispatcher = Dispatchers.Default
) : ViewModel() {

    private val _uiState = MutableStateFlow(
        AskQuestionUiState(
            modelStatus = modelStatusProvider()
        )
    )
    val uiState: StateFlow<AskQuestionUiState> = _uiState.asStateFlow()

    init {
        // Observe reactive memory count from SQLite
        viewModelScope.launch {
            dao.getAllAsFlow().collect { records ->
                _uiState.update { it.copy(memoryCount = records.size) }
            }
        }
    }

    fun onQueryChanged(newQuery: String) {
        _uiState.update {
            it.copy(
                query = newQuery,
                errorMessage = null
            )
        }
    }

    fun onSpeechResult(spokenText: String) {
        _uiState.update {
            it.copy(
                query = spokenText,
                errorMessage = null
            )
        }
        // Auto-run query on voice capture for instant UX
        askQuestion(spokenText)
    }

    fun onSpeechError(error: String) {
        _uiState.update { it.copy(errorMessage = error) }
    }

    fun refreshModelStatus() {
        _uiState.update {
            it.copy(modelStatus = modelStatusProvider())
        }
    }

    fun askQuestion(explicitQuery: String? = null) {
        val targetQuery = (explicitQuery ?: _uiState.value.query).trim()
        if (targetQuery.isBlank()) {
            _uiState.update { it.copy(errorMessage = "Please enter or speak a question.") }
            return
        }

        viewModelScope.launch {
            try {
                // Stage 1: Retrieval
                _uiState.update {
                    it.copy(
                        query = targetQuery,
                        isSearching = true,
                        isGenerating = false,
                        loadingMessage = "Searching memories...",
                        answer = null,
                        errorMessage = null,
                        retrievedMemories = emptyList()
                    )
                }

                val retrievedHits = withContext(ioDispatcher) {
                    searchService.search(targetQuery, poolK = 20, topK = 5)
                }

                _uiState.update {
                    it.copy(
                        isSearching = false,
                        isGenerating = true,
                        loadingMessage = "Synthesizing answer with Gemma 4...",
                        retrievedMemories = retrievedHits
                    )
                }

                // Stage 2: On-Device Generation
                val generationResult = withContext(defaultDispatcher) {
                    if (answerGenerator != null) {
                        answerGenerator.invoke(targetQuery, retrievedHits.map { it.first })
                    } else if (generator != null) {
                        generator.generateAnswer(
                            question = targetQuery,
                            contextMemories = retrievedHits.map { it.first }
                        )
                    } else {
                        GenerationResult(
                            answer = "Gemma 4 model runtime not initialized.",
                            latencyMs = 0L,
                            isModelFound = false,
                            fullPrompt = ""
                        )
                    }
                }

                _uiState.update {
                    it.copy(
                        isGenerating = false,
                        loadingMessage = "",
                        answer = generationResult.answer,
                        latencyMs = generationResult.latencyMs,
                        modelStatus = modelStatusProvider()
                    )
                }

            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isSearching = false,
                        isGenerating = false,
                        loadingMessage = "",
                        errorMessage = "Error answering question: ${e.localizedMessage ?: e.message}"
                    )
                }
            }
        }
    }

    companion object {
        fun provideFactory(
            application: android.content.Context,
            dao: MemoryDao,
            searchService: SearchService
        ): ViewModelProvider.Factory = object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T {
                if (modelClass.isAssignableFrom(AskQuestionViewModel::class.java)) {
                    val app = application.applicationContext
                    val gen = LiteRTGenerator(app)
                    return AskQuestionViewModel(
                        dao = dao,
                        searchService = searchService,
                        generator = gen,
                        modelStatusProvider = { ModelManager.getModelStatus(app) }
                    ) as T
                }
                throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
            }
        }
    }
}
