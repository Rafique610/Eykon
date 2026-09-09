package com.eykon.memory

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.ui.Modifier
import com.eykon.memory.ui.screens.AddMemoryScreen
import com.eykon.memory.ui.theme.EykonMemoryTheme
import com.eykon.memory.ui.viewmodels.AddMemoryViewModel

class MainActivity : ComponentActivity() {

    private val viewModel: AddMemoryViewModel by viewModels {
        val dao = (application as MemoryApp).database.memoryDao()
        AddMemoryViewModel.provideFactory(dao)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            EykonMemoryTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
                    AddMemoryScreen(
                        viewModel = viewModel,
                        modifier = Modifier.padding(innerPadding)
                    )
                }
            }
        }
    }
}
