import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(kw_only=True)
class MemoryRecord:
    """Data model representing a single memory record."""
    text: str
    embedding: list[float]
    timestamp: datetime
    source_type: str = "text"
    id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert record to dictionary representation."""
        return {
            "id": self.id,
            "text": self.text,
            "embedding": self.embedding,
            "timestamp": self.timestamp.isoformat(),
            "source_type": self.source_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryRecord":
        """Construct a MemoryRecord from dictionary data."""
        raw_timestamp = data["timestamp"]
        if isinstance(raw_timestamp, str):
            timestamp = datetime.fromisoformat(raw_timestamp)
        elif isinstance(raw_timestamp, datetime):
            timestamp = raw_timestamp
        else:
            raise ValueError(f"Invalid timestamp format: {raw_timestamp}")

        raw_embedding = data.get("embedding", [])
        if isinstance(raw_embedding, str):
            embedding = json.loads(raw_embedding)
        else:
            embedding = list(raw_embedding)

        return cls(
            id=data.get("id"),
            text=data["text"],
            embedding=embedding,
            timestamp=timestamp,
            source_type=data.get("source_type", "text"),
        )
