# Step 05 — Video Processing Orchestrator (End-to-End Pipeline)

## What
Build `src/vision/processor.py` — the orchestrator that ties together frame extraction (Step 03) and VLM captioning (Step 04) into a single `process_video()` function. Given a video file, it produces a list of timestamped captions ready to be stored as memories.

## Why
This is the "glue" module. It handles the video processing workflow, progress reporting, and error recovery. It does NOT touch the memory database — that's Step 06's job. This separation lets us test the vision pipeline independently from the storage layer.

## How to Implement

### 5.1 Module Structure

```
src/vision/
├── __init__.py      (updated)
├── extractor.py     (Step 03)
├── captioner.py     (Step 04)
├── processor.py     ← this step
```

### 5.2 `src/vision/processor.py`

```python
"""End-to-end video processing: extract frames → caption each → return timestamped results."""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from src.vision.extractor import ExtractedFrame, extract_frames, get_video_info
from src.vision.captioner import caption_image


@dataclass
class CaptionedFrame:
    """A video frame with its generated text caption."""
    caption: str                 # VLM-generated description
    timestamp_seconds: float     # position in video
    frame_index: int             # 0-based extracted frame index
    video_path: str              # source file
    video_filename: str          # basename for metadata


def process_video(
    video_path: str | Path,
    interval_seconds: float | None = None,
    caption_prompt: str | None = None,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> list[CaptionedFrame]:
    """Process an entire video file: extract frames → caption each.

    Args:
        video_path: Path to the video file.
        interval_seconds: Override frame sampling interval.
        caption_prompt: Override the VLM prompt.
        on_progress: Optional callback(current_frame, total_frames, caption)
                     for UI progress bars.

    Returns:
        List of CaptionedFrame objects, ordered by timestamp.
    """
    ...


def format_timestamp(seconds: float) -> str:
    """Convert seconds to human-readable format: 'MM:SS' or 'HH:MM:SS'."""
    ...
```

### 5.3 Key Implementation Details

1. **Flow:** `process_video()` calls `extract_frames()` → iterates over frames → calls `caption_image()` for each → wraps results in `CaptionedFrame`.
2. **Progress callback:** The `on_progress` callback is designed for Streamlit's progress bar. It receives `(current_frame_number, total_frames, latest_caption)`.
3. **Error resilience:** If captioning fails for one frame (e.g., OOM spike), log a warning and skip it rather than crashing the entire batch. The caption for that frame becomes `"[Frame could not be captioned]"`.
4. **Timestamp formatting:** `format_timestamp(185.5)` → `"03:05"`. Used in memory text prefixing.
5. **Memory text format:** Each caption is prefixed with its timestamp: `"[03:05] User is holding a red book on a kitchen counter."` — this timestamp prefix is critical for time-based queries.

### 5.4 Update `src/vision/__init__.py`

Add exports: `CaptionedFrame`, `process_video`, `format_timestamp`.

## Verification
- [ ] `process_video("test_video.mp4")` returns a list of `CaptionedFrame` objects
- [ ] Each caption is non-empty and relevant to the video content
- [ ] Timestamps are monotonically increasing
- [ ] Progress callback fires for each frame
- [ ] A 60-second video at 5s interval produces ~12 captioned frames
- [ ] If one frame fails to caption, the rest still process successfully

### Terminal Test Command
```bash
uv run python -c "
from src.vision import process_video

def on_progress(current, total, caption):
    print(f'  [{current}/{total}] {caption[:60]}...')

results = process_video('test_video.mp4', interval_seconds=5, on_progress=on_progress)
print(f'\nProcessed {len(results)} frames:')
for r in results:
    print(f'  [{r.timestamp_seconds:.1f}s] {r.caption}')
"
```

## Files Changed
- [NEW] `src/vision/processor.py`
- [MODIFY] `src/vision/__init__.py` — add processor exports

## Dependencies
- Step 03 (extractor)
- Step 04 (captioner)

## Common Issues
- Long videos (>30 min) will produce hundreds of frames — each captioned sequentially. Expect ~2-5 seconds per frame on GPU. A 2-hour video at 5s interval = 1440 frames × 3s = ~72 minutes processing time. Document this for the panel.
- GPU memory may spike during processing. Monitor with `psutil` or `nvidia-smi`.
