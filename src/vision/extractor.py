"""Video frame extraction using OpenCV."""
from pathlib import Path
from dataclasses import dataclass
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


def get_video_info(video_path: str | Path) -> dict:
    """Return metadata about a video file: duration, fps, resolution, total frames."""
    path = str(video_path)
    if not Path(path).exists():
        raise FileNotFoundError(f"Video file not found: {path}")

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f"OpenCV cannot open video: {path}")

    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = (total_frames / fps) if fps > 0 else 0.0

        return {
            "fps": fps,
            "total_frames": total_frames,
            "width": width,
            "height": height,
            "duration": duration,
        }
    finally:
        cap.release()


def extract_frames(
    video_path: str | Path,
    interval_seconds: float | None = None,
) -> list[ExtractedFrame]:
    """Extract frames from a video file at regular intervals."""
    path = str(video_path)
    if not Path(path).exists():
        raise FileNotFoundError(f"Video file not found: {path}")
        
    s = Settings()
    interval = interval_seconds if interval_seconds is not None else s.FRAME_INTERVAL_SECONDS

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f"OpenCV cannot open video: {path}")

    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0.0
        
        extracted = []
        frame_idx = 0
        target_seconds = 0.0
        
        # Include exactly the boundaries like 10.0s for a 10s video
        while target_seconds <= duration + 0.01:
            target_frame = int(target_seconds * fps)
            # Ensure we don't ask for a frame past the end
            target_frame = min(target_frame, max(0, total_frames - 1))
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            ret, frame = cap.read()
            
            # OpenCV sometimes fails on the exact last frame of some containers
            if not ret and target_frame > 0:
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame - 1)
                ret, frame = cap.read()
                
            if ret:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb_frame)
                extracted.append(ExtractedFrame(
                    image=img,
                    timestamp_seconds=target_seconds,
                    frame_index=frame_idx,
                    video_path=path,
                ))
                frame_idx += 1
                
            target_seconds += interval

        # Force the final frame if there is a gap (e.g. video is 9.96s but interval is 5.0)
        last_extracted_ts = extracted[-1].timestamp_seconds if extracted else -1
        if duration - last_extracted_ts > interval * 0.2:
            target_frame = max(0, total_frames - 1)
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            ret, frame = cap.read()
            if not ret and target_frame > 0:
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame - 1)
                ret, frame = cap.read()
                
            if ret:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb_frame)
                extracted.append(ExtractedFrame(
                    image=img,
                    timestamp_seconds=duration,
                    frame_index=frame_idx,
                    video_path=path,
                ))

        return extracted
    finally:
        cap.release()
