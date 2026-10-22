from contextlib import closing
from datetime import datetime

import streamlit as st

from src.config import Settings
from src.video_memory import db
from src.video_memory.capture import UploadError, save_upload


def render() -> None:
    settings = Settings()
    st.header("Video memory")
    st.caption("Add a recorded clip with sound. It is stored on this device and nothing is sent anywhere.")

    with st.form("video_upload", clear_on_submit=True):
        uploaded = st.file_uploader(
            "Add a video",
            type=settings.video_types,
            help=f"Up to {settings.video_max_mb} MB. Types: {', '.join(settings.video_types)}.",
        )
        submitted = st.form_submit_button("Save video", type="primary", use_container_width=True)

    if not submitted:
        return
    if uploaded is None:
        st.error("Choose a video file first.")
        return

    try:
        with st.spinner("Saving the video and reading its details…"), closing(db.connect()) as conn:
            video, meta = save_upload(conn, uploaded)
    except UploadError as error:
        st.error(str(error))
        return

    recorded = datetime.fromisoformat(video.recorded_at)
    when = f"Recorded {recorded:%d %b %Y, %H:%M} UTC" if meta["from_file"] else f"Uploaded {recorded:%d %b %Y, %H:%M} UTC (the file carries no recording time)"
    place = f", at {video.lat:.4f}, {video.lon:.4f}" if video.lat is not None else ""
    st.success(f"Saved. {when}, {video.duration_s:.0f} s{place}.")
    st.caption(f"Stored as `{video.file_path}`. Processing starts in a later step.")
