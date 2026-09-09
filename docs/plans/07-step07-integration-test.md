# Step 07 — Integration Test on Real Device + Polish

**Status:** 🔲 Not started  
**Depends on:** Steps 01–06  
**Blocks:** Nothing (final step)

---

## What This Step Does

End-to-end testing on the real arm64 test device, error handling for edge
cases, and README/setup documentation for anyone else trying to run it (your
supervisor included, if they want to try it themselves).

## Why This Matters

A demo that crashes is worse than no demo — same principle as Phase 1 Step 08,
now with real-device and offline-mode risk added on top of the desktop
version's concerns.

---

## What Gets Done

| Area | Work |
|---|---|
| Offline Testing | Airplane mode checks |
| Edge Cases | Empty DB, long input, Whisper garbage output, Storage full |
| Error Handling | Dialogs/Snackbars for model load failures |
| Demo Tools | Hidden "Load Samples" button for fast presentation |
| Documentation | README updates for Android |

---

## ⚖️ Decisions to Make

### 1. Sample data for fast demo setup

It takes time to type/speak 5 memories in front of a supervisor. 

| Option | Pros | Cons |
|---|---|---|
| Manually enter data | Real demonstration | Slow |
| Hidden "Load Samples" | Instant population | Needs specific UI |

**Recommendation:** Same as Phase 1. Add a small bug icon or hidden long-press target in the `TopAppBar` that inserts 5 pre-defined `MemoryRecord` instances into the DB. This allows the demo to jump straight into the "Ask" phase if time is tight.

### 2. Error Handling UX

| Error | How to Handle |
|---|---|
| Download fails | Full screen error on Setup screen + Retry button. |
| Storage full | Native Android Toast + prevent download attempt. |
| Whisper empty | Show snackbar: "Could not hear anything clearly." |
| LLM timeout/crash | Replace answer with: "Engine error. Try again." |

**Recommendation:** Implement specific UI states for these 4 critical failure modes. Do not let the app crash silently.

### 3. README Content for Android

**Recommendation:** 
Update `README.md` to include:
- Required Device Specs (arm64, ~4GB RAM, 3GB storage).
- Compilation Instructions (Android Studio, JDK 17).
- First Launch Expectations (Needs internet once for 2.4GB download).

---

## How to Implement

### 1. Add "Load Samples" Debug Feature
In `AddMemoryViewModel.kt`:
```kotlin
fun loadDemoSamples() {
    val samples = listOf(
        "I have a dentist appointment with Dr. Smith on Tuesday the 14th at 3pm.",
        "My brother's name is Ali.",
        "The project codename is Eykon and it focuses on local AI."
    )
    viewModelScope.launch {
        samples.forEach { TextCaptureService.createMemoryFromText(it).let { r -> dao.insert(r) } }
        loadMemoryCount()
    }
}
```
Trigger this via a long-press on the app title in the `TopAppBar`.

### 2. README Update
```markdown
## Android Build (Phase 2)

1. Open `android/` folder in Android Studio.
2. Connect a physical **arm64** Android device (Emulators usually run x86_64 and will fail to run the LiteRT native libraries).
3. Build and Run.
4. **First Launch:** The app requires internet to download the 2.4GB Gemma model. Wait for the Setup Screen to finish.
5. **Offline:** Once downloaded, turn on Airplane Mode. The app runs 100% locally.
```

---

## Verification Checklist

- [ ] **Install:** App installs and runs on the real device (not the emulator).
- [ ] **First Run:** Model downloads on first launch with visible progress and passes its checksum check.
- [ ] **Offline:** Full loop works fully offline once setup is complete (Airplane Mode ON).
- [ ] **Capture:** Both text and voice capture work, are embedded correctly, and are retrievable.
- [ ] **Generation:** A question with no relevant stored memory produces "I don't have that information" rather than a hallucinated answer.
- [ ] **Resilience:** App doesn't crash on any of the tested edge cases (e.g., hitting "Ask" with empty text, hitting "Save" with empty text).

---

## Research Notes

- [ ] Verify how Android WorkManager handles interrupted downloads (e.g. user closes app halfway). Does it resume? Make sure the UI reflects this.

---

## Files Changed

- `ui/screens/AddMemoryScreen.kt` (Add Load Samples trigger)
- `ui/viewmodels/AddMemoryViewModel.kt` (Add Load Samples logic)
- `README.md` (Update for Android instructions)
