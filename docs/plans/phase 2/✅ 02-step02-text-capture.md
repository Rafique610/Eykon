# Step 02 — Text Capture (Ported Loop, No ML Yet)

**Status:** ✅ Done  
**Depends on:** Step 01  
**Blocks:** Steps 05, 06

---

## What This Step Does

A minimal Compose screen where the user types a memory and it gets saved to Room,
with no embedding or model involved yet — just proving the native Android capture +
storage loop works before any ML risk is introduced.

## Why This Matters

Isolates "does the basic app loop work on this device" from "does the model
work on this device." If something breaks later, you'll know it's the model
layer, not a fundamental app/storage issue. This mirrors how Phase 1 started
with capture and storage before embeddings.

---

## What Gets Created

```
app/src/main/java/com/eykon/memory/
├── capture/
│   └── TextCaptureService.kt       ← Validates input, creates MemoryRecord
├── ui/
│   └── screens/
│       └── AddMemoryScreen.kt      ← Compose screen: text field + save button
└── MainActivity.kt                 ← Wires up the screen
```

---

## ⚖️ Decisions to Make

### 1. Text validation rules

How strict should input validation be?

| Rule | Strict | Lenient (Phase 1 approach) |
|---|---|---|
| Empty text | Reject | Reject |
| Min length | 3+ characters | Any non-empty |
| Max length | 10,000 chars | No limit |
| Whitespace only | Reject | Reject |

**Recommendation:** Match Phase 1 — reject empty/whitespace-only input, no
min/max length otherwise. The user should be free to write what they want.

---

### 2. Placeholder embedding value

Since real embeddings arrive in Step 04, what to store in the embedding field
for now?

| Option | Value | Pros | Cons |
|---|---|---|---|
| Empty JSON array | `"[]"` | Clean, obviously placeholder | Breaks cosine sim if forgotten |
| Zeros vector | `"[0.0, 0.0, ...]"` (384 zeros) | Correct dimension, benign for search | 384 zeros is verbose |
| Null/empty string | `""` | Minimal | Breaks TypeConverter |

**Recommendation:** Empty JSON array `"[]"`. It's obvious, parseable, and
Steps 04/06 will replace it with real embeddings. Add a TODO comment marking
this as a placeholder.

---

### 3. UI state management pattern

| Pattern | Complexity | Compose-friendly |
|---|---|---|
| ViewModel + StateFlow | Standard, recommended | ✅ Yes |
| Remember + mutableStateOf | Simpler, no ViewModel | ✅ Yes, but doesn't survive config change |
| Hilt + ViewModel | Full DI | Overkill for Phase 2 |

**Recommendation:** ViewModel + StateFlow. It's the standard Compose pattern,
survives configuration changes (screen rotation), and makes wiring up
repository calls with coroutines straightforward. No DI framework needed —
just pass the database instance from `MemoryApp`.

---

### 4. Show saved memories on-screen?

| Option | What the user sees | Purpose |
|---|---|---|
| Just confirmation toast | "Memory saved!" | Minimal |
| Confirmation + list of recent memories | "Memory saved!" + scrollable list | Proves storage works |
| Database Inspector only | Nothing visible | Debugging only |

**Recommendation:** Confirmation + temporary list of recent memories (last 5).
This doubles as visual verification during development and will be repurposed
in Step 06's full UI. Show memory count in a badge or subtitle.

---

### 5. Chunking in this step?

Phase 1 used token-bounded chunking (256 avg, 30–50 overlap, 400 ceiling). Should
Step 02 implement chunking now?

**Recommendation:** No. Skip chunking for now — save a single MemoryRecord per
input. Chunking requires the tokenizer (tied to the embedding model in Step 04).
Add chunking when the embedding wrapper is ready. This keeps Step 02 focused on
proving the capture → storage loop without ML dependencies.

---

## How to Implement

### 1. Create `TextCaptureService.kt`

```kotlin
// capture/TextCaptureService.kt
package com.eykon.memory.capture

import com.eykon.memory.data.MemoryRecord
import java.time.Instant

/**
 * Validates raw text input and produces a MemoryRecord ready for storage.
 * No embedding or ML involved — placeholder embedding for now.
 */
object TextCaptureService {
    
    fun createMemoryFromText(text: String): MemoryRecord {
        val cleaned = text.trim()
        require(cleaned.isNotEmpty()) { "Memory text cannot be empty or whitespace only" }
        
        return MemoryRecord(
            text = cleaned,
            embedding = "[]",  // TODO: Replace with real embedding in Step 04
            timestamp = Instant.now().toString(),
            sourceType = "text",
            metadata = """{"chunk_index": 0, "total_chunks": 1, "token_count": 0}"""
        )
    }
}
```

### 2. Create `AddMemoryViewModel.kt`

```kotlin
// ui/viewmodels/AddMemoryViewModel.kt
class AddMemoryViewModel(private val dao: MemoryDao) : ViewModel() {
    
    private val _uiState = MutableStateFlow(AddMemoryUiState())
    val uiState: StateFlow<AddMemoryUiState> = _uiState.asStateFlow()
    
    fun saveMemory(text: String) {
        viewModelScope.launch {
            try {
                val record = TextCaptureService.createMemoryFromText(text)
                val id = dao.insert(record)
                _uiState.update { it.copy(
                    savedMessage = "Memory saved! (ID: $id)",
                    memoryCount = dao.count(),
                    inputText = ""
                )}
            } catch (e: IllegalArgumentException) {
                _uiState.update { it.copy(errorMessage = e.message) }
            }
        }
    }
    
    fun loadMemoryCount() {
        viewModelScope.launch {
            _uiState.update { it.copy(memoryCount = dao.count()) }
        }
    }
}

data class AddMemoryUiState(
    val inputText: String = "",
    val savedMessage: String? = null,
    val errorMessage: String? = null,
    val memoryCount: Int = 0,
)
```

### 3. Create `AddMemoryScreen.kt`

```kotlin
// ui/screens/AddMemoryScreen.kt
@Composable
fun AddMemoryScreen(viewModel: AddMemoryViewModel) {
    val uiState by viewModel.uiState.collectAsState()
    var text by remember { mutableStateOf("") }
    
    Column(modifier = Modifier.padding(16.dp)) {
        Text("Add a New Memory", style = MaterialTheme.typography.headlineMedium)
        Spacer(modifier = Modifier.height(16.dp))
        
        OutlinedTextField(
            value = text,
            onValueChange = { text = it },
            label = { Text("Type your memory here...") },
            modifier = Modifier.fillMaxWidth().height(150.dp),
            maxLines = 6,
        )
        Spacer(modifier = Modifier.height(8.dp))
        
        Button(
            onClick = {
                viewModel.saveMemory(text)
                text = ""
            },
            modifier = Modifier.fillMaxWidth()
        ) { Text("💾 Save Memory") }
        
        // Feedback
        uiState.savedMessage?.let {
            Text(it, color = MaterialTheme.colorScheme.primary)
        }
        uiState.errorMessage?.let {
            Text(it, color = MaterialTheme.colorScheme.error)
        }
        
        // Memory count
        Text("📊 Total memories: ${uiState.memoryCount}",
             style = MaterialTheme.typography.bodyMedium)
    }
}
```

### 4. Wire up in `MainActivity.kt`

```kotlin
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val db = (application as MemoryApp).database
        setContent {
            MemoryTheme {
                val viewModel = viewModel { AddMemoryViewModel(db.memoryDao()) }
                AddMemoryScreen(viewModel)
            }
        }
    }
}
```

---

## Verification

### On-Device Test (real arm64 device)

```bash
# Build and install
./gradlew installDebug

# Launch the app
adb shell am start -n com.eykon.memory/.MainActivity
```

Manual checks:
1. Type "I have a dentist appointment on the 14th" → tap Save → confirm
   "Memory saved!" message appears.
2. Type empty text → tap Save → confirm error message.
3. Type whitespace → tap Save → confirm error message.
4. Save 3 memories → confirm memory count shows 3.

### Database Verification

```bash
# Check the database exists
adb shell run-as com.eykon.memory ls databases/

# Use Android Studio's Database Inspector (App Inspection tab)
# to visually confirm saved records with correct fields.
```

---

## Research Notes

> _Leave your notes here as you research._

- [ ] ViewModel factory pattern without Hilt — how to pass DAO?
  (ViewModelProvider.Factory or `viewModel { }` with SavedStateHandle)
- [ ] Does `Instant.now().toString()` produce ISO 8601 on all API levels ≥ 26?
- [ ] Compose TextField state management best practices?
- [ ] Should we use Navigation Compose now, or wire it up in Step 06?

---

## Files Changed

- `capture/TextCaptureService.kt` (new — text validation + MemoryRecord creation)
- `ui/viewmodels/AddMemoryViewModel.kt` (new — UI state management)
- `ui/screens/AddMemoryScreen.kt` (new — Compose screen)
- `MainActivity.kt` (updated — wires the screen)
