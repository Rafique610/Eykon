# Step 05 — Whisper Voice Capture

**Status:** 🔲 Not started  
**Depends on:** Step 02  
**Blocks:** Step 06

---

## What This Step Does

Adds a record button that captures audio, transcribes it locally via Whisper,
and feeds the resulting text through the exact same path as typed text
(validation, embedding, storage), tagged with source_type "audio".

## Why This Matters

Keeps the architecture's core promise: every input becomes a text memory
record regardless of source. Whisper's only job is producing that text; nothing
downstream needs to know or care that it came from a voice recording.

---

## What Gets Created

```
app/src/main/java/com/eykon/memory/
├── capture/
│   ├── AudioCaptureService.kt       ← Manages audio recording (MediaRecorder)
│   └── WhisperTranscriber.kt        ← Wraps whisper.cpp for Android
└── ui/
    └── components/
        └── VoiceRecordButton.kt     ← Hold-to-record or Tap-to-record UI
```

---

## ⚖️ Decisions to Make

### 1. Whisper Model Size

We need an on-device STT model.

| Size | Memory | Speed | Accuracy |
|---|---|---|---|
| Tiny (en) | ~75 MB | Very Fast | Okay |
| Base (en) | ~140 MB | Fast | Good |
| Small (en) | ~460 MB | Slower | Excellent |

**Recommendation:** Start with the **"tiny.en"** or **"base.en"** model. You're already carrying a 2.4GB LLM and an embedding model, so keeping the STT model small matters for total storage and load time. If accuracy is poor during testing, upgrade to Base.

### 2. What happens to the raw audio after transcription?

**Recommendation:** Discard it. The architecture only needs the text; keeping raw audio files around adds storage and privacy surface area with no clear benefit at this phase. Just save it temporarily in `Context.cacheDir`, transcribe, and delete.

### 3. Error handling for poor transcription

**Recommendation:** Show the transcript to the user before saving (not auto-saved silently), so they can catch and fix obvious transcription errors. This also doubles as a demo moment showing the STT step is real.

### 4. Audio format

**Recommendation:** `whisper.cpp` usually expects 16kHz WAV (16-bit PCM). Use Android's `AudioRecord` to capture 16kHz PCM directly, bypassing the need to transcode compressed formats like AAC/M4A.

---

## How to Implement

### 1. `WhisperTranscriber.kt`
Include a maintained `whisper.cpp` Android wrapper (e.g., via Maven Central or copying the JNI wrapper from the official `whisper.cpp` repo).
```kotlin
package com.eykon.memory.capture

class WhisperTranscriber(modelPath: String) {
    // Initialize whisper context
    
    suspend fun transcribe(audioFilePath: String): String {
        // Run transcription on background thread
        // Return resulting string
    }
}
```

### 2. `VoiceRecordButton.kt` (UI Component)
```kotlin
@Composable
fun VoiceRecordButton(onRecordingComplete: (String) -> Unit) {
    // Requires RECORD_AUDIO permission
    // UI: A microphone icon that turns red while holding
    // On release: stops AudioRecord, writes WAV to cache, calls Whisper
    // Returns the transcript string to the parent screen
}
```

### 3. Wiring it together
In `AddMemoryScreen`, when the `VoiceRecordButton` returns a transcript, inject it into the same `TextField` used for typing. This satisfies Decision #3 (showing the user the transcript so they can edit it before hitting "Save Memory").

---

## Verification

1. **Permissions Check:** App correctly requests `RECORD_AUDIO` permission.
2. **Audio Check:** Record a spoken memory ("My favorite color is blue").
3. **Transcription Check:** The transcript appears in the text box. Edit it if necessary.
4. **Storage Check:** Save it. Confirm it's saved with `sourceType = "audio"` in the DB inspector.
5. **Retrieval Check:** Confirm a later question can retrieve and be answered from an audio-sourced memory, same as a typed one.

---

## Research Notes

- [ ] Check `whisper.cpp` Android integration docs. Is there a pre-built AAR, or do we need to compile the NDK library? (Look for `com.whispercpp:whisper-android` or similar).
- [ ] Implement a clean `AudioRecord` to WAV utility to ensure 16kHz 16-bit PCM format.

---

## Files Changed

- `app/build.gradle.kts` (Add whisper wrapper dependency, NDK config if needed)
- `AndroidManifest.xml` (Add `<uses-permission android:name="android.permission.RECORD_AUDIO" />`)
- `capture/AudioCaptureService.kt` (new)
- `capture/WhisperTranscriber.kt` (new)
- `ui/components/VoiceRecordButton.kt` (new)
- `ui/screens/AddMemoryScreen.kt` (Update to include VoiceRecordButton)
