# Step 06 — Integration With Existing Memory Pipeline

## What
Connect the video processing pipeline (Step 05) to the existing `src/memories/` module. Video captions become `MemoryRecord` objects with `source_type="video"` and are stored, embedded, and retrievable through the same hybrid search pipeline used for text memories.

## Why
This is the critical integration step. The entire Phase 1 architecture was designed for this moment — the PROJECT_SPEC says: *"later phases only require new capture adapters, not changes to storage, retrieval, or generation."* This step proves that claim.

## How to Implement

### 6.1 Add `create_memories_from_video()` to `src/memories/service.py`

```python
def create_memories_from_video(
    captioned_frames: list["CaptionedFrame"],
    video_filename: str,
    embedder: Embedder | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[MemoryRecord]:
    """Convert captioned video frames into embeddable MemoryRecords.

    Each caption is stored as a separate memory record with:
    - source_type = "video"
    - metadata includes: video_filename, timestamp_seconds, frame_index
    - Text is prefixed with timestamp: "[MM:SS] caption text"
    """
    ...
```

### 6.2 Key Implementation Details

1. **Memory text format:** Each caption is stored as `"[03:05] User placed car keys on kitchen counter."` — the timestamp prefix helps both retrieval and the LLM understand temporal context.

2. **Metadata enrichment:** Each `MemoryRecord.metadata` includes:
   ```python
   {
       "source": "video",
       "video_filename": "morning_routine.mp4",
       "timestamp_seconds": 185.5,
       "frame_index": 37,
       "total_frames": 120,       # total captioned frames in this video
   }
   ```

3. **Chunking strategy:** Individual captions are short (1 sentence, ~20–50 tokens), well under the 256-token chunk size. They should NOT be chunked further — each caption becomes exactly 1 `MemoryRecord`. Only if a caption somehow exceeds the chunk ceiling do we apply the existing `chunk_text_by_tokens()`.

4. **Batch embedding:** Use `embedder.embed_batch()` for all captions at once (much faster than one-by-one).

5. **Batch saving:** Use `save_memories()` for a single-transaction insert.

### 6.3 Update `src/memories/__init__.py`

Export `create_memories_from_video`.

### 6.4 Update `src/memories/query.py` — Concept Map Extension

Add vision-related concepts to `CONCEPT_MAP`:
```python
"keys": "key keychain table counter pocket door lock car",
"left": "placed put set down forgot left behind dropped",
"wearing": "shirt jacket hat glasses shoes clothes outfit",
"cooking": "kitchen stove pan pot food cutting chopping",
"reading": "book page paper document screen tablet phone",
```

### 6.5 Integration Verification Script

Add a Taskfile entry `test-vision-integration`:
```yaml
test-vision-integration:
  desc: Process a test video, store as memories, then query them
  cmd: uv run python -c "
    from src.memories import init_db, Embedder, save_memories, search_memories
    from src.memories.service import create_memories_from_video
    from src.vision import process_video
    init_db()
    embedder = Embedder()
    frames = process_video('test_video.mp4', interval_seconds=10)
    records = create_memories_from_video(frames, 'test_video.mp4', embedder)
    ids = save_memories(records)
    print(f'Stored {len(ids)} video memories')
    results = search_memories('where did I put my keys', embedder, top_k=3)
    for r in results:
        print(f'  [{r.score:.4f}] {r.record.text[:80]}')
  "
```

## Verification
- [ ] Video captions are stored in SQLite with `source_type="video"`
- [ ] Each record's `metadata` contains video filename, timestamp, and frame index
- [ ] `search_memories("where did I leave my keys")` retrieves video-sourced memories alongside text memories
- [ ] The existing text-based memories are NOT broken (run `task test` — must still pass)
- [ ] FTS5 indexes the video caption text (keyword search works on video memories)
- [ ] The existing benchmark (`task benchmark`) still passes without regression

### Terminal Test Commands
```bash
# Regression check — existing pipeline must still work
task test

# New integration test
task test-vision-integration
```

## Files Changed
- [MODIFY] `src/memories/service.py` — add `create_memories_from_video()`
- [MODIFY] `src/memories/__init__.py` — export `create_memories_from_video`
- [MODIFY] `src/memories/query.py` — extend CONCEPT_MAP with vision-related terms
- [MODIFY] `Taskfile.yml` — add `test-vision-integration` task

## Dependencies
- Step 05 (processor provides `CaptionedFrame` objects)
- Phase 1 modules (all reused as-is)

## Common Issues
- If video captions are too generic ("A person is standing in a room"), retrieval quality will suffer. This is addressed in Experiment A3 (caption prompt tuning).
- Ensure `datetime.now()` is used for `timestamp` field (when the memory was created), NOT the video's in-file timestamp. The video timestamp goes into `metadata["timestamp_seconds"]`.
