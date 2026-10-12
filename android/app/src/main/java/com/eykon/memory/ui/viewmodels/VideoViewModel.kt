package com.eykon.memory.ui.viewmodels

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.eykon.memory.video.SavedVideo
import com.eykon.memory.video.UploadException
import com.eykon.memory.video.Video
import com.eykon.memory.video.VideoCapture
import com.eykon.memory.video.VideoRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

data class VideoUiState(
    val isSaving: Boolean = false,
    val saved: SavedVideo? = null,
    val errorMessage: String? = null,
    val videos: List<Video> = emptyList(),
)

class VideoViewModel(
    private val capture: VideoCapture,
    private val repository: VideoRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(VideoUiState())
    val uiState: StateFlow<VideoUiState> = _uiState.asStateFlow()

    init {
        refresh()
    }

    fun onVideoPicked(uri: Uri?) {
        if (uri == null) return
        _uiState.update { it.copy(isSaving = true, saved = null, errorMessage = null) }
        viewModelScope.launch {
            try {
                val saved = withContext(Dispatchers.IO) { capture.save(uri) }
                _uiState.update { it.copy(isSaving = false, saved = saved) }
            } catch (e: UploadException) {
                _uiState.update { it.copy(isSaving = false, errorMessage = e.message) }
            } catch (e: Exception) {
                _uiState.update { it.copy(isSaving = false, errorMessage = "The video could not be saved (${e.javaClass.simpleName}).") }
            }
            refresh()
        }
    }

    private fun refresh() {
        viewModelScope.launch {
            val videos = withContext(Dispatchers.IO) { repository.list() }
            _uiState.update { it.copy(videos = videos) }
        }
    }

    companion object {
        fun provideFactory(capture: VideoCapture, repository: VideoRepository): ViewModelProvider.Factory =
            object : ViewModelProvider.Factory {
                @Suppress("UNCHECKED_CAST")
                override fun <T : ViewModel> create(modelClass: Class<T>): T = VideoViewModel(capture, repository) as T
            }
    }
}
