package com.eykon.memory

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import com.eykon.memory.retrieval.SearchService
import com.eykon.memory.ui.navigation.AppNavigation
import com.eykon.memory.ui.theme.EykonMemoryTheme
import com.eykon.memory.ui.viewmodels.AddMemoryViewModel
import com.eykon.memory.ui.viewmodels.AskQuestionViewModel
import com.eykon.memory.ui.viewmodels.VideoViewModel
import com.eykon.memory.video.VideoCapture
import com.eykon.memory.video.VideoRepository
import com.eykon.memory.video.VideoSearch

class MainActivity : ComponentActivity() {

    private val addMemoryViewModel: AddMemoryViewModel by viewModels {
        val dao = (application as MemoryApp).database.memoryDao()
        AddMemoryViewModel.provideFactory(dao, applicationContext)
    }

    private val askQuestionViewModel: AskQuestionViewModel by viewModels {
        val app = application as MemoryApp
        val dao = app.database.memoryDao()
        val searchService = SearchService(dao)
        AskQuestionViewModel.provideFactory(app, dao, searchService)
    }

    private val videoViewModel: VideoViewModel by viewModels {
        val app = application as MemoryApp
        val repository = VideoRepository { app.database.openHelper.writableDatabase }
        VideoViewModel.provideFactory(
            VideoCapture(applicationContext, repository, app.videoJobs), repository, app::kickVideoWorker,
        ) { text -> VideoSearch.frames(app.database.openHelper.writableDatabase, text) }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            EykonMemoryTheme {
                AppNavigation(
                    addMemoryViewModel = addMemoryViewModel,
                    askQuestionViewModel = askQuestionViewModel,
                    videoViewModel = videoViewModel
                )
            }
        }
    }
}
