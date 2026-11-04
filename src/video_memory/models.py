from dataclasses import dataclass


@dataclass(kw_only=True)
class Video:
    video_id: str
    file_path: str
    recorded_at: str
    created_at: str
    duration_s: float = 0.0
    lat: float | None = None
    lon: float | None = None
    status: str = "processing"


@dataclass(kw_only=True)
class Frame:
    video_id: str
    frame_no: int
    t_s: float
    path: str
    id: int | None = None
    phash: str | None = None
    kept: int = 1
    drop_reason: str | None = None


@dataclass(kw_only=True)
class AudioSegment:
    video_id: str
    start_s: float
    end_s: float
    is_speech: int
    loudness_db: float
    id: int | None = None


@dataclass(kw_only=True)
class TranscriptChunk:
    video_id: str
    start_s: float
    end_s: float
    text: str
    id: int | None = None
    language: str | None = None
    speaker: str | None = None
    confidence: float | None = None


@dataclass(kw_only=True)
class SceneRecord:
    frame_id: int
    objects: str
    caption: str
    source: str
    action: str | None = None
    place: str | None = None
    people: int = 0


@dataclass(kw_only=True)
class VideoText:
    video_id: str
    source: str
    ref_id: int
    start_s: float
    end_s: float
    text: str
    id: int | None = None


@dataclass(kw_only=True)
class AudioWindow:
    video_id: str
    start_s: float
    end_s: float
    id: int | None = None
