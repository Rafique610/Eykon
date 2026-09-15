# Step 06 — Full UI (Text + Voice + Retrieved Memories)

**Status:** 🔲 Not started  
**Depends on:** Steps 02, 03, 04, 05  
**Blocks:** Step 07

---

## What This Step Does

Assembles the pieces from Steps 02-05 into the actual demo-facing app: a way
to add memories (typed or spoken), a way to ask questions, and a way to see
the answer along with which memories were retrieved.

## Why This Matters

This is what your supervisor actually sees and interacts with. The Phase 1
Streamlit UI already proved which presentation choices work well for a demo —
this step is largely about porting those same decisions natively, not
re-deciding them.

---

## What Gets Created

```
app/src/main/java/com/eykon/memory/ui/
├── navigation/
│   └── AppNavigation.kt             ← Bottom Nav / Routes
├── screens/
│   ├── AskQuestionScreen.kt         ← Question input, Answer text, Retrieved memories
│   └── AddMemoryScreen.kt           ← (Updated) Final styling
└── components/
    ├── MemoryCountBadge.kt
    └── RetrievedMemoryCard.kt       ← UI for showing retrieval transparency
```

---

## ⚖️ Decisions to Make

### 1. Navigation

| Option | Pros | Cons |
|---|---|---|
| Bottom Navigation | Native Android feel, 1-tap switch | Uses bottom screen space |
| Top Tabs | Good for 2 pages | Harder to reach on large phones |
| Drawer | Hidden | Extra tap required |

**Recommendation:** Match Phase 1's two-destination structure (Add / Ask) using standard Android **Bottom Navigation**. 

### 2. Memory Count / Status Display

**Recommendation:** Keep it visible at all times, same reasoning as Phase 1 — the user should always know the app's state. Put a `TopAppBar` on both screens showing:
`🧠 Eykon Memory   [ 🟢 Model Ready | 📊 12 mems ]`

### 3. Displaying Retrieved Memories

The spec requires that the retrieval step is *visible*.

**Recommendation:** Mirror Phase 1. Beneath the generated LLM answer, include an expandable section (or just a list) titled `📚 Retrieved Memories (X found)`. Show the memory text and the cosine similarity score `(0.87)`.

### 4. Loading States

**Recommendation:**
- Retrieval: `st.spinner("Searching...")` → Use `CircularProgressIndicator` + "Searching memories..."
- Generation: `st.spinner("Generating...")` → Use `CircularProgressIndicator` + "Generating answer... (this may take a moment)"

Given the 10-30s generation latency on mobile, the UI **must** remain responsive and clearly indicate that the model is working.

---

## How to Implement

### 1. `AppNavigation.kt`
Use Jetpack Navigation Compose.
```kotlin
@Composable
fun AppNavigation() {
    val navController = rememberNavController()
    Scaffold(
        bottomBar = { BottomNavigationBar(navController) }
    ) { innerPadding ->
        NavHost(navController, startDestination = "ask", Modifier.padding(innerPadding)) {
            composable("add") { AddMemoryScreen() }
            composable("ask") { AskQuestionScreen() }
        }
    }
}
```

### 2. `AskQuestionScreen.kt`
```kotlin
@Composable
fun AskQuestionScreen(viewModel: AskQuestionViewModel) {
    val uiState by viewModel.uiState.collectAsState()
    
    Column {
        // Input Area
        OutlinedTextField(value = query, onValueChange = ...)
        Button(onClick = { viewModel.askQuestion(query) }) { Text("Ask") }
        
        // Loading State
        if (uiState.isLoading) {
            CircularProgressIndicator()
            Text(uiState.loadingMessage) // "Searching..." or "Generating..."
        }
        
        // Answer Area
        uiState.answer?.let {
            Text("💡 Answer", fontWeight = FontWeight.Bold)
            Text(it)
        }
        
        // Context Area (Transparency)
        if (uiState.retrievedMemories.isNotEmpty()) {
            Text("📚 Retrieved Context")
            LazyColumn {
                items(uiState.retrievedMemories) { (record, score) ->
                    Text("${record.text} ($score)")
                }
            }
        }
    }
}
```

---

## Verification

**Full manual walkthrough:**
1. Open App. Ensure Bottom Nav works.
2. Go to Add page. Add a typed memory. Add a spoken memory.
3. Go to Ask page. 
4. Ask a question that should hit the typed memory. Verify loading text changes appropriately. Verify answer is correct. Verify context is shown.
5. Ask a question that should hit the spoken memory. Verify answer.
6. Ask a question with no relevant memory (e.g. "What is my cat's name?"). Verify the LLM says "I don't have that information" and does not hallucinate.

---

## Research Notes

- [ ] Check Jetpack Compose Material 3 `NavigationBar` implementation for Bottom Nav.
- [ ] Check if UI jitter occurs during heavy LLM inference. If so, ensure `LiteRTGenerator` is properly relegated to a background dispatcher (`Dispatchers.Default` or `IO`).

---

## Files Changed

- `ui/navigation/AppNavigation.kt` (new)
- `ui/screens/AskQuestionScreen.kt` (new)
- `ui/screens/AddMemoryScreen.kt` (update)
- `MainActivity.kt` (update to mount `AppNavigation`)
