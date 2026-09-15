# Step 03 — Frame Extraction Module

## What
Build `src/vision/extractor.py` — a module that takes a video file path, extracts frames at a configurable interval (default: 1 frame per 5 seconds), and yields them as PIL Images with timestamp metadata.

## Why
This is the first stage of the video pipeline. We isolate frame extraction from captioning so each can be tested and benchmarked independently. On mobile, the extraction logic would use Android's MediaCodec instead of OpenCV, but the interface stays identical.

## How to Implement

### 3.1 Create Feature Folder

```
src/vision/
├── __init__.py
├── extractor.py     ← this step
```

### 3.2 `src/vision/extractor.py`

```python
"""Video frame extraction using OpenCV."""
from pathlib import Path
from dataclasses import dataclass
from datetime import timedelta
import cv2
from PIL import Image

from src.config import Settings


@dataclass
class ExtractedFrame:
    """A single frame extracted from a video file."""
    image: Image.Image          # PIL Image (RGB)
    timestamp_seconds: float    # position in video (seconds)
    frame_index: int            # 0-based index of this extracted frame
    video_path: str             # source video file path


def extract_frames(
    video_path: str | Path,
    interval_seconds: float | None = None,
) -> list[ExtractedFrame]:
    """Extract frames from a video file at regular intervals.

    Args:
        video_path: Path to the video file (.mp4, .avi, .mov, etc.)
        interval_seconds: Seconds between extracted frames. Defaults to Settings.FRAME_INTERVAL_SECONDS.

    Returns:
        List of ExtractedFrame objects.

    Raises:
        FileNotFoundError: If video file doesn't exist.
        RuntimeError: If OpenCV can't open the video.
    """
    ...


def get_video_info(video_path: str | Path) -> dict:
    """Return metadata about a video file: duration, fps, resolution, total frames."""
    ...
```

### 3.3 Key Implementation Details

1. **Use OpenCV `cv2.VideoCapture`** to open the video file.
2. **Calculate frame positions:** Given `interval_seconds` and the video's FPS, compute which frame numbers to extract (e.g., at 30fps with 5s interval → frames 0, 150, 300, ...).
3. **Convert BGR → RGB → PIL Image:** OpenCV reads in BGR; convert to RGB, then to `PIL.Image` for VLM compatibility.
4. **Timestamp calculation:** `frame_number / fps = seconds`. Store as float.
5. **Resource cleanup:** Always release the `VideoCapture` object, even on error.

### 3.4 `src/vision/__init__.py`

```python
"""Vision feature module: video processing and VLM captioning."""
from src.vision.extractor import ExtractedFrame, extract_frames, get_video_info

__all__ = ["ExtractedFrame", "extract_frames", "get_video_info"]
```

## Verification
- [ ] `extract_frames("test_video.mp4")` returns a list of `ExtractedFrame` objects
- [ ] Frame count matches expected: a 60-second video at 5s interval → 12 frames (±1)
- [ ] Each frame's `timestamp_seconds` is approximately correct (within 0.2s)
- [ ] Each frame's `.image` is a valid PIL Image with correct dimensions
- [ ] `get_video_info()` returns correct duration, fps, resolution
- [ ] Handles edge cases: missing file (FileNotFoundError), corrupt video (RuntimeError), zero-length video (empty list)

### Terminal Test Command
```bash
uv run python -c "
from src.vision import extract_frames, get_video_info
info = get_video_info('test_video.mp4')
print('Video info:', info)
frames = extract_frames('test_video.mp4', interval_seconds=5)
print(f'Extracted {len(frames)} frames')
for f in frames[:3]:
    print(f'  Frame {f.frame_index}: {f.timestamp_seconds:.1f}s, size={f.image.size}')
"
```

## Files Changed
- [NEW] `src/vision/__init__.py`
- [NEW] `src/vision/extractor.py`

## Dependencies
- Step 02 (opencv-python must be installed)

## Common Issues
- Some video codecs may not be supported by OpenCV's default build — if a video fails to open, install `opencv-python-headless` with ffmpeg support
- Very large videos (>2GB) should still work since we seek to specific frames, not read sequentially
- Windows paths with spaces need `str(Path(...))` conversion
