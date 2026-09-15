# Step 07 — Streamlit UI: Video Upload & Processing Page

## What
Add a third page to the Streamlit app: **🎬 Process Video** — where the user uploads a video file, watches it being processed frame-by-frame with a progress bar, and then can immediately query the extracted memories.

## Why
The PoC must be demonstrable to the panel. A working UI that shows the video being processed and then answers questions about it is the single most convincing demo artifact.

## How to Implement

### 7.1 Add New Page to Sidebar

In `src/ui/app.py`, add `"🎬 Process Video"` to the page radio:
```python
page = st.radio(
    "Navigate",
    ["📝 Add Memory", "❓ Ask Question", "🎬 Process Video"],
    label_visibility="collapsed",
)
```

### 7.2 Video Processing Page Layout

```
🎬 Process Video
├── File uploader (accepts .mp4, .avi, .mov, .mkv)
├── Settings expander
│   ├── Frame interval slider (1-30 seconds, default 5)
│   └── Caption prompt text input
├── "🚀 Process Video" button
├── Progress section (appears during processing)
│   ├── Video info (duration, fps, resolution)
│   ├── Progress bar (X of Y frames)
│   ├── Live caption preview (shows latest caption as it's generated)
│   └── Elapsed time
├── Results section (appears after processing)
│   ├── Summary: "Extracted X frames, stored Y memories in Z seconds"
│   ├── Expandable list of all captions with timestamps
│   └── Quick query input: "Ask about this video"
```

### 7.3 Key Implementation Details

1. **File upload:** Streamlit's `st.file_uploader` returns bytes. Save to a temp file, process, then clean up.
2. **Progress bar:** Use `st.progress()` + the `on_progress` callback from `process_video()`.
3. **Live preview:** Show the latest caption in a `st.empty()` placeholder that updates each frame.
4. **Immediate query:** After processing, show a text input so the user can immediately ask questions about the video without switching pages.
5. **Session state:** Store the processing results in `st.session_state` so they survive reruns.

### 7.4 Processing Flow

```python
# Pseudocode for the page
uploaded = st.file_uploader("Upload a video", type=["mp4", "avi", "mov", "mkv"])

if uploaded and st.button("🚀 Process Video"):
    # 1. Save uploaded bytes to temp file
    # 2. Show video info
    # 3. Process with progress bar
    # 4. Store captions as memories
    # 5. Show results summary
    # 6. Enable immediate querying
```

## Verification
- [ ] Video upload accepts .mp4, .avi, .mov, .mkv formats
- [ ] Progress bar updates smoothly during processing
- [ ] Live caption preview shows each caption as it's generated
- [ ] After processing, all captions are visible in expandable list
- [ ] The "Ask about this video" quick query works and returns relevant answers
- [ ] Processing a 1-minute test video completes successfully
- [ ] Sidebar memory count updates after video processing
- [ ] Existing pages (Add Memory, Ask Question) still work correctly

### Terminal Test Command
```bash
# Start the app and manually test the video upload page
task run
```

## Files Changed
- [MODIFY] `src/ui/app.py` — add "🎬 Process Video" page with upload, processing, and query UI

## Dependencies
- Step 05 (process_video)
- Step 06 (create_memories_from_video, save_memories)

## Common Issues
- Streamlit's file uploader has a default 200MB limit. For large videos, increase with `server.maxUploadSize` in `.streamlit/config.toml`.
- Processing is synchronous and blocks the UI. For very long videos (>10 min), warn the user about expected processing time before starting.
- Temp file cleanup: use `tempfile.NamedTemporaryFile` with `delete=False`, then manually delete after processing.
