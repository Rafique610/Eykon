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

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            EykonMemoryTheme {
                AppNavigation(
                    addMemoryViewModel = addMemoryViewModel,
                    askQuestionViewModel = askQuestionViewModel
                )
            }
        }
    }
}
