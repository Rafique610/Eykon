"""End-to-end video processing: extract frames → caption each → return timestamped results."""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import logging

from src.vision.extractor import ExtractedFrame, extract_frames, get_video_info
from src.vision.captioner import caption_image

logger = logging.getLogger(__name__)


@dataclass
class CaptionedFrame:
    """A video frame with its generated text caption."""
    caption: str                 # VLM-generated description
    timestamp_seconds: float     # position in video
    frame_index: int             # 0-based extracted frame index
    video_path: str              # source file
    video_filename: str          # basename for metadata


def format_timestamp(seconds: float) -> str:
    """Convert seconds to human-readable format: 'MM:SS' or 'HH:MM:SS'."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02}:{minutes:02}:{secs:02}"
    return f"{minutes:02}:{secs:02}"


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
    video_path_str = str(video_path)
    video_filename = Path(video_path).name

    # 1. Extract frames
    frames = extract_frames(video_path_str, interval_seconds=interval_seconds)
    total_frames = len(frames)
    
    captioned_frames = []
    
    # 2. Caption each frame
    for i, frame in enumerate(frames):
        try:
            caption = caption_image(frame.image, prompt=caption_prompt)
        except Exception as e:
            logger.warning(f"Failed to caption frame {i} at {frame.timestamp_seconds:.1f}s: {e}")
            caption = "[Frame could not be captioned]"
            
        timestamp_str = format_timestamp(frame.timestamp_seconds)
        # Prefix the caption with the timestamp
        formatted_caption = f"[{timestamp_str}] {caption}"
        
        captioned_frame = CaptionedFrame(
            caption=formatted_caption,
            timestamp_seconds=frame.timestamp_seconds,
            frame_index=i,
            video_path=video_path_str,
            video_filename=video_filename
        )
        captioned_frames.append(captioned_frame)
        
        if on_progress:
            try:
                on_progress(i + 1, total_frames, formatted_caption)
            except Exception as e:
                logger.error(f"Error in on_progress callback: {e}")

    return captioned_frames
