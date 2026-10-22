package com.eykon.memory.ui.viewmodels

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.eykon.memory.video.FrameHit
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
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

data class VideoUiState(
    val isSaving: Boolean = false,
    val saved: SavedVideo? = null,
    val errorMessage: String? = null,
    val videos: List<VideoWithJob> = emptyList(),
    val query: String = "",
    val isSearching: Boolean = false,
    /** Null until a search has run; the phrase it ran for is [searchedFor]. */
    val hits: List<FrameHit>? = null,
    val searchedFor: String = "",
    val searchMs: Long = 0,
    val searchError: String? = null,
    /** "Your video from 7 Oct is ready to search.", shown once when a video finishes while the app is open. */
    val readyNotice: String? = null,
)

class VideoViewModel(
    private val capture: VideoCapture,
    private val repository: VideoRepository,
    private val startProcessing: () -> Unit,
    private val searchFrames: (String) -> List<FrameHit>,
    private val retryJob: (Long) -> Unit,
) : ViewModel() {

    private val _uiState = MutableStateFlow(VideoUiState())
    val uiState: StateFlow<VideoUiState> = _uiState.asStateFlow()

    private var watching: Job? = null

    /** The ready videos already seen, so each one is announced once. Null until the list has been loaded once. */
    private var knownReady: Set<String>? = null

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

    fun onQueryChanged(text: String) = _uiState.update { it.copy(query = text) }

    /** Find the stored frames that best match the typed phrase. */
    fun onSearch() {
        val text = _uiState.value.query.trim()
        if (text.isEmpty() || _uiState.value.isSearching) return
        _uiState.update { it.copy(isSearching = true, searchError = null) }
        viewModelScope.launch {
            try {
                val start = System.nanoTime()
                val hits = withContext(Dispatchers.Default) { searchFrames(text) }
                _uiState.update { it.copy(isSearching = false, hits = hits, searchedFor = text, searchMs = (System.nanoTime() - start) / 1_000_000) }
            } catch (e: Exception) {
                _uiState.update { it.copy(isSearching = false, hits = null, searchError = e.message ?: "The search failed (${e.javaClass.simpleName}).") }
            }
        }
    }

    /** Put a failed job back in the queue; it starts again at the stage that failed. */
    fun onRetry(jobId: Long) {
        viewModelScope.launch {
            withContext(Dispatchers.IO) { retryJob(jobId) }
            startProcessing()
            watchJobs()
        }
    }

    /** Reload the list, and keep reloading once a second only while a job is still waiting or running. */
    private fun watchJobs() {
        if (watching?.isActive == true) return
        watching = viewModelScope.launch {
            do {
                val videos = withContext(Dispatchers.IO) { repository.listWithJobs() }
                val ready = videos.filter { it.video.status == "ready" }
                val fresh = knownReady?.let { known -> ready.firstOrNull { it.video.videoId !in known } }
                knownReady = ready.map { it.video.videoId }.toSet()
                val notice = fresh?.let { "Your video from ${NOTICE_DATE.format(Instant.parse(it.video.recordedAt).atZone(ZoneId.systemDefault()))} is ready to search." }
                _uiState.update { it.copy(videos = videos, readyNotice = notice ?: it.readyNotice) }
                val busy = videos.any { it.jobStatus == "queued" || it.jobStatus == "running" }
                if (busy) delay(1000)
            } while (busy)
        }
    }

    companion object {
        private val NOTICE_DATE = DateTimeFormatter.ofPattern("d MMM", Locale.ENGLISH)

        fun provideFactory(
            capture: VideoCapture,
            repository: VideoRepository,
            startProcessing: () -> Unit,
            searchFrames: (String) -> List<FrameHit>,
            retryJob: (Long) -> Unit,
        ): ViewModelProvider.Factory =
            object : ViewModelProvider.Factory {
                @Suppress("UNCHECKED_CAST")
                override fun <T : ViewModel> create(modelClass: Class<T>): T =
                    VideoViewModel(capture, repository, startProcessing, searchFrames, retryJob) as T
            }
    }
}
