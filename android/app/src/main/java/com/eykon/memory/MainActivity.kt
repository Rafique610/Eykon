package com.eykon.memory

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import com.eykon.memory.ui.screens.AddMemoryScreen
import com.eykon.memory.ui.screens.GenerationTestScreen
import com.eykon.memory.ui.theme.EykonMemoryTheme
import com.eykon.memory.ui.viewmodels.AddMemoryViewModel
import com.eykon.memory.ui.viewmodels.GenerationTestViewModel

class MainActivity : ComponentActivity() {

    private val addMemoryViewModel: AddMemoryViewModel by viewModels {
        val dao = (application as MemoryApp).database.memoryDao()
        AddMemoryViewModel.provideFactory(dao)
    }

    private val generationTestViewModel: GenerationTestViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            EykonMemoryTheme {
                var selectedTab by remember { mutableIntStateOf(0) }

                Scaffold(
                    modifier = Modifier.fillMaxSize(),
                    bottomBar = {
                        NavigationBar {
                            NavigationBarItem(
                                selected = selectedTab == 0,
                                onClick = { selectedTab = 0 },
                                icon = { Text("📝") },
                                label = { Text("Capture") }
                            )
                            NavigationBarItem(
                                selected = selectedTab == 1,
                                onClick = {
                                    selectedTab = 1
                                    generationTestViewModel.refreshModelStatus()
                                },
                                icon = { Text("🤖") },
                                label = { Text("Generation") }
                            )
                        }
                    }
                ) { innerPadding ->
                    when (selectedTab) {
                        0 -> AddMemoryScreen(
                            viewModel = addMemoryViewModel,
                            modifier = Modifier.padding(innerPadding)
                        )
                        1 -> GenerationTestScreen(
                            viewModel = generationTestViewModel,
                            modifier = Modifier.padding(innerPadding)
                        )
                    }
                }
            }
        }
    }
}
