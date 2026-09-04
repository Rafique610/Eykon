import json
from dataclasses import dataclass, field
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
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert record to dictionary representation."""
        return {
            "id": self.id,
            "text": self.text,
            "embedding": self.embedding,
            "timestamp": self.timestamp.isoformat(),
            "source_type": self.source_type,
            "metadata": self.metadata,
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

        raw_metadata = data.get("metadata", {})
        if isinstance(raw_metadata, str):
            try:
                metadata = json.loads(raw_metadata) if raw_metadata else {}
            except json.JSONDecodeError:
                metadata = {}
        elif isinstance(raw_metadata, dict):
            metadata = dict(raw_metadata)
        else:
            metadata = {}

        return cls(
            id=data.get("id"),
            text=data["text"],
            embedding=embedding,
            timestamp=timestamp,
            source_type=data.get("source_type", "text"),
            metadata=metadata,
        )

