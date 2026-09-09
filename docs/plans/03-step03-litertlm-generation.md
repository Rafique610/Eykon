# Step 03 — LiteRT-LM Generation Integration

**Status:** 🔲 Not started  
**Depends on:** Step 01  
**Blocks:** Steps 04, 06

---

## What This Step Does

Gets Gemma 4 E2B running on-device via the LiteRT-LM Android (Kotlin) API,
using a hardcoded/canned prompt and context — deliberately not wired to real
retrieval yet.

## Why This Matters

This is the single highest-risk unknown in Phase 2: does a ~2.4GB model
actually load and generate acceptably on your test device. Proving it works in
isolation, before retrieval is layered on top, means a failure here is
unambiguous — it's the model/runtime, not a bug in your retrieval wiring.

---

## What Gets Created

```
app/src/main/java/com/eykon/memory/
├── ml/
│   ├── generator/
│   │   ├── LiteRTGenerator.kt       ← Wraps LiteRT-LM API calls
│   │   └── GenerationParams.kt      ← Holds temp, topK, etc.
│   └── download/
│       ├── ModelDownloadWorker.kt   ← WorkManager job for 2.4GB download
│       └── ModelManager.kt          ← Checks if model exists/checksums
└── ui/
    └── screens/
        └── GenerationTestScreen.kt  ← Canned test harness UI
```

---

## ⚖️ Decisions to Make

### 1. Model Download Trigger

The 2.4GB Gemma model cannot be bundled in the APK.

| Option | Pros | Cons |
|---|---|---|
| Background sync | Invisible to user | App broken until it finishes silently |
| Blocking Setup Screen | Clear state, explicit progress | Delays app usage on first open |
| On-demand (Ask page) | Fast initial install | Bad UX when trying to ask a question |

**Recommendation:** Blocking Setup Screen. Check on app first-launch; if the model isn't present or fails its checksum, route to a dedicated setup screen with a WorkManager-driven progress bar and a storage-space check before allowing the user into the rest of the app.

---

### 2. Where to Store the Model File

| Location | Pros | Cons |
|---|---|---|
| Internal Storage (`Context.getFilesDir`) | Private, no permissions | Tighter OS quotas on some devices |
| External App Storage (`Context.getExternalFilesDir`) | Larger quota, auto-cleaned on uninstall | Technically accessible via USB |
| Public Downloads | Easy to inspect | Requires permissions, messy |

**Recommendation:** App-specific external files directory (`Context.getExternalFilesDir(null)`). It provides the space needed for a 2.4GB file without triggering internal storage quota warnings, and requires no explicit user permissions on modern Android versions.

---

### 3. Execution Context (Threading)

| Approach | Details |
|---|---|
| Main Thread | Will crash/ANR instantly. |
| Kotlin Coroutines (`Dispatchers.Default`) | Best for CPU-bound generation tasks. |
| Dedicated ThreadPool | Good, but verbose. |

**Recommendation:** Use Coroutines. Run the `LiteRTGenerator.generate()` call inside `withContext(Dispatchers.Default) { ... }` so it does not block the UI thread, allowing Compose to show a loading spinner.

---

### 4. Generation Parameters

**Recommendation:** Match the Phase 1 desktop settings:
- `temperature`: ~0.1 (strict, factual)
- `max_tokens`: 256
Adjust only if on-device generation quality or speed demands it.

---

## How to Implement

### 1. `ModelDownloadWorker.kt`
Set up Android WorkManager to download the `.litertlm` file. Include a checksum validation step (`MessageDigest.getInstance("SHA-256")`). 

### 2. `LiteRTGenerator.kt`
```kotlin
package com.eykon.memory.ml.generator

import com.google.ai.edge.litert.llm.InferenceEngine // (hypothetical/current import path)
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class LiteRTGenerator(modelPath: String) {
    private val engine = InferenceEngine.create(modelPath)
    
    suspend fun generateAnswer(prompt: String): String = withContext(Dispatchers.Default) {
        // Run inference on background thread
        val result = engine.generate(prompt, temperature = 0.1f, maxTokens = 256)
        return@withContext result.text
    }
}
```

### 3. `GenerationTestScreen.kt`
Create a temporary Compose screen with a hardcoded QA prompt based on Phase 1's `build_rag_prompt`.
```kotlin
@Composable
fun GenerationTestScreen(viewModel: GenerationTestViewModel) {
    // Show download progress if model missing, 
    // Otherwise show a button: "Run Test Generation"
    // Output: Text(viewModel.generatedAnswer)
}
```

---

## Verification

1. **Install on real device:** MUST be an arm64 Android device.
2. **First Launch:** Confirm the app checks for the model, prompts download, and successfully downloads ~2.4GB to the correct directory.
3. **Offline Check:** Turn on Airplane Mode.
4. **Generate:** Tap "Run Test Generation". Ensure the UI doesn't freeze (spinner should spin) and a coherent text response appears in < 30 seconds.

---

## Research Notes

- [ ] Confirm exact LiteRT-LM dependency string for Android `build.gradle.kts`.
- [ ] Determine best URL/Hosting for the `.litertlm` model file for the WorkManager to fetch from during demo.
- [ ] Verify SHA-256 checksum of the target `gemma-4-E2B-it.litertlm` file for the validator.

---

## Files Changed

- `app/build.gradle.kts` (Add LiteRT-LM, WorkManager)
- `ml/download/ModelDownloadWorker.kt` (new)
- `ml/download/ModelManager.kt` (new)
- `ml/generator/LiteRTGenerator.kt` (new)
- `ui/screens/GenerationTestScreen.kt` (new)
