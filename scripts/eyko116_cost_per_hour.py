"""EYKO-116 Part 2 (b): storage cost of one hour of video, calculated.

cost/hour = (video bitrate x 3600 s) + 16 kHz audio + (kept frames/hour x bytes per kept frame) + frame rows

Every input below is a measurement from the repo or the kit; the source of each is in the comment. Run:
    python scripts/eyko116_cost_per_hour.py
"""

HOUR = 3600
MB = 1_000_000

# Bitrate of the file (ffprobe format.bit_rate) and its length, so the copy = source size is shown, not assumed.
CLIPS = {
    "PXL_20261014_094359202 (camera)": dict(bitrate=20_026_221, seconds=74.5, kept=10, sightings=53),   # ffprobe; kept/sightings: Part 3 runs
    "PXL_20261014_094903187 (camera)": dict(bitrate=20_029_953, seconds=75.0, kept=16, sightings=134),
    "screen recording (Part 2)":       dict(bitrate=round(675_833_518 * 8 / 3606), seconds=3606,  kept=21, sightings=48),  # 4 clips = 675,833,518 B over 60.1 min (= the 675.8 MB of copies measured): 1.5 Mbps, not the nominal 1.25
    # 11-12 Nov, test movie (a feature film) cut with -c copy into 5, 10, 15, 25 min: sources 1,058,844,930 B over 3,300.46 s; 831 kept frames, 1,604 sightings
    "movie, 4 pieces (11 Nov)":        dict(bitrate=round(1_058_844_930 * 8 / 3300.46), seconds=3300.46, kept=831, sightings=1604),
}
# Growth of the app's data folder measured on the Infinix (bytes): screen run 757 MiB; movie run 1,181,126 KB (1,231,422 - 50,296 KB)
MEASURED_GROWTH = {"screen recording (Part 2)": 757 * 1024 * 1024, "movie, 4 pieces (11 Nov)": 1_181_126 * 1024}

AUDIO_PER_HOUR = 115.4 * MB          # audio16k.wav: 16,000 Hz x 2 bytes x 3600 s (Part 2: 115.4 MB for 60.1 min)

# From db-after-part2 (21 kept frames, 48 sightings): per kept frame, in bytes.
PICTURE = 936 * 1024 / 21            # kept frame file, 936 KB / 21 (screen frames; camera frames may be larger)
IMAGE_VEC, TEXT_VEC = 2048, 1536     # 512 and 384 float32 numbers, as stored (length(embedding))
TEXT_ROWS = 331 + 57                 # scene_records + video_texts text per kept frame
SIGHTING_BYTES = 99154 / 48          # one object_sightings row, ~2,066 B (mostly its embedding)
FRAME_ROW = 100                      # one row of `frames` (about 100 B), written for EVERY sampled frame
FRAMES_PER_SEC = 3                   # 10,820 rows / 3,606 s; camera clips 224 frames / 75 s


def per_hour(bitrate, kept_per_s, sightings_per_kept):
    copy = bitrate * HOUR / 8
    per_kept = PICTURE + IMAGE_VEC + TEXT_VEC + TEXT_ROWS + sightings_per_kept * SIGHTING_BYTES
    frames = kept_per_s * HOUR * per_kept
    rows = FRAMES_PER_SEC * HOUR * FRAME_ROW
    return copy, AUDIO_PER_HOUR, frames, rows


print(f"{'clip':36} {'copy GB':>8} {'audio MB':>9} {'kept MB':>8} {'rows MB':>8} {'total GB/h':>10} {'measured GB/h':>14} {'diff':>6}")
for name, c in CLIPS.items():
    kept_s, sp = c["kept"] / c["seconds"], c["sightings"] / c["kept"]
    copy, audio, frames, rows = per_hour(c["bitrate"], kept_s, sp)
    total = copy + audio + frames + rows
    measured = MEASURED_GROWTH.get(name)
    m_per_h = measured * HOUR / c["seconds"] if measured else None
    tail = f"{m_per_h / 1e9:14.2f} {100 * (total - m_per_h) / m_per_h:+5.1f}%" if m_per_h else f"{'(calculated)':>14}"
    print(f"{name:36} {copy/1e9:8.2f} {audio/MB:9.1f} {frames/MB:8.1f} {rows/MB:8.1f} {total/1e9:10.2f} {tail}")
