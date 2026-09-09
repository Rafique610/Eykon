package com.eykon.memory.ui.viewmodels

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.eykon.memory.capture.TextCaptureService
import com.eykon.memory.data.MemoryDao
import com.eykon.memory.data.MemoryRecord
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class AddMemoryUiState(
    val inputText: String = "",
    val savedMessage: String? = null,
    val errorMessage: String? = null,
    val isSaving: Boolean = false
)

class AddMemoryViewModel(private val dao: MemoryDao) : ViewModel() {

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

    fun saveMemory() {
        val currentText = _uiState.value.inputText
        viewModelScope.launch {
            try {
                _uiState.update { it.copy(isSaving = true, errorMessage = null) }
                val record = TextCaptureService.createMemoryFromText(currentText)
                val id = dao.insert(record)
                _uiState.update {
                    it.copy(
                        inputText = "",
                        savedMessage = "Memory saved! (ID: #$id)",
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

    companion object {
        fun provideFactory(dao: MemoryDao): ViewModelProvider.Factory = object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T {
                if (modelClass.isAssignableFrom(AddMemoryViewModel::class.java)) {
                    return AddMemoryViewModel(dao) as T
                }
                throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
            }
        }
    }
}
