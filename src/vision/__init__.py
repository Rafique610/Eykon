"""Vision feature module: video processing and VLM captioning."""
from src.vision.extractor import ExtractedFrame, extract_frames, get_video_info

__all__ = ["ExtractedFrame", "extract_frames", "get_video_info"]
