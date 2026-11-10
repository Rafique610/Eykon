package com.eykon.memory

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.core.content.ContextCompat
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
            { text -> VideoSearch.frames(app.database.openHelper.writableDatabase, text) },
            app.videoJobs::retry,
        )
    }

    /** EYKO-44: Android 13+ asks before an app may show the "processing video" notification. Without it the job still runs, just unseen. */
    private val notificationPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
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
