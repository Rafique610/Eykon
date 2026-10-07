package com.eykon.memory.ui.navigation

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.sp
import com.eykon.memory.ui.screens.AddMemoryScreen
import com.eykon.memory.ui.screens.AskQuestionScreen
import com.eykon.memory.ui.viewmodels.AddMemoryViewModel
import com.eykon.memory.ui.viewmodels.AskQuestionViewModel

enum class NavDestination(val label: String, val icon: String) {
    CAPTURE("Capture", "📝"),
    ASK("Ask", "💬")
}

@Composable
fun AppNavigation(
    addMemoryViewModel: AddMemoryViewModel,
    askQuestionViewModel: AskQuestionViewModel,
    modifier: Modifier = Modifier
) {
    var selectedIndex by rememberSaveable { mutableIntStateOf(NavDestination.ASK.ordinal) }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        bottomBar = {
            NavigationBar {
                NavDestination.values().forEachIndexed { index, destination ->
                    NavigationBarItem(
                        selected = selectedIndex == index,
                        onClick = {
                            selectedIndex = index
                            if (destination == NavDestination.ASK) {
                                askQuestionViewModel.refreshModelStatus()
                            }
                        },
                        icon = {
                            Text(destination.icon, fontSize = 20.sp)
                        },
                        label = {
                            Text(destination.label)
                        }
                    )
                }
            }
        }
    ) { innerPadding ->
        when (NavDestination.values()[selectedIndex]) {
            NavDestination.CAPTURE -> {
                AddMemoryScreen(
                    viewModel = addMemoryViewModel,
                    modifier = Modifier.padding(innerPadding)
                )
            }
            NavDestination.ASK -> {
                AskQuestionScreen(
                    viewModel = askQuestionViewModel,
                    modifier = Modifier.padding(innerPadding)
                )
            }
        }
    }
}
