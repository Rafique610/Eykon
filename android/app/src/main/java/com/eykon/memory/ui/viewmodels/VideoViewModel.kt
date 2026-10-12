package com.eykon.memory.ui.viewmodels

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.eykon.memory.video.SavedVideo
import com.eykon.memory.video.UploadException
import com.eykon.memory.video.VideoCapture
import com.eykon.memory.video.VideoRepository
import com.eykon.memory.video.VideoWithJob
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
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
    val videos: List<VideoWithJob> = emptyList(),
)

class VideoViewModel(
    private val capture: VideoCapture,
    private val repository: VideoRepository,
    private val startProcessing: () -> Unit,
) : ViewModel() {

    private val _uiState = MutableStateFlow(VideoUiState())
    val uiState: StateFlow<VideoUiState> = _uiState.asStateFlow()

    private var watching: Job? = null

    init {
        watchJobs()
    }

    fun onVideoPicked(uri: Uri?) {
        if (uri == null) return
        _uiState.update { it.copy(isSaving = true, saved = null, errorMessage = null) }
        viewModelScope.launch {
            try {
                val saved = withContext(Dispatchers.IO) { capture.save(uri) }
                _uiState.update { it.copy(isSaving = false, saved = saved) }
                startProcessing()
            } catch (e: UploadException) {
                _uiState.update { it.copy(isSaving = false, errorMessage = e.message) }
            } catch (e: Exception) {
                _uiState.update { it.copy(isSaving = false, errorMessage = "The video could not be saved (${e.javaClass.simpleName}).") }
            }
            watchJobs()
        }
    }

    /** Reload the list, and keep reloading once a second only while a job is still waiting or running. */
    private fun watchJobs() {
        if (watching?.isActive == true) return
        watching = viewModelScope.launch {
            do {
                val videos = withContext(Dispatchers.IO) { repository.listWithJobs() }
                _uiState.update { it.copy(videos = videos) }
                val busy = videos.any { it.jobStatus == "queued" || it.jobStatus == "running" }
                if (busy) delay(1000)
            } while (busy)
        }
    }

    companion object {
        fun provideFactory(capture: VideoCapture, repository: VideoRepository, startProcessing: () -> Unit): ViewModelProvider.Factory =
            object : ViewModelProvider.Factory {
                @Suppress("UNCHECKED_CAST")
                override fun <T : ViewModel> create(modelClass: Class<T>): T =
                    VideoViewModel(capture, repository, startProcessing) as T
            }
    }
}
