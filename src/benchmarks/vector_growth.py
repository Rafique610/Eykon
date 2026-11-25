"""EYKO-101: how many vectors a user has after 1, 3, 6 and 12 months. Run: task vector-growth

vectors per day = minutes of video recorded per day x kept frames per minute (one image vector per kept frame).
Kept frames per minute come from our own runs (files in docs/results); minutes per day come from published studies
(docs/results/vector-growth/sources.md). Writes docs/results/vector-growth/: vector-growth.csv (month by month),
vector-growth.json (every input and result) and vector-growth.png/.svg.
"""

import csv
import json
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/results/vector-growth"
DAYS_PER_MONTH = 365.25 / 12

# Step 1. Kept frames (= image_vec rows = text_vec rows; audio_vec stays 0, no speech stage writes audio windows yet).
CAMERA_CLIPS = [  # name, kept frames, seconds, source file
    ("kit clip 1 (Pixel camera, walking)", 10, 74.5, "docs/results/head3/stage_times.csv (dedup frames_out, 21 runs, 3 phones)"),
    ("kit clip 2 (Pixel camera, walking)", 16, 74.9, "docs/results/head3/stage_times.csv (dedup frames_out, 21 runs, 3 phones)"),
    ("Ego4D 57c09157 (head-worn)", 156, 480, "docs/results/2026-10-20-ego4d-baseline.md, On the phone, Pixel"),
    ("Ego4D f21ba0cf (head-worn)", 69, 480, "docs/results/2026-10-20-ego4d-baseline.md, On the phone, Pixel"),
    ("Ego4D c7873f07 (head-worn)", 113, 480, "docs/results/2026-10-20-ego4d-baseline.md, On the phone, Pixel"),
    ("Ego4D ffc52dc7 (head-worn)", 34, 228, "docs/results/2026-10-20-ego4d-baseline.md, On the phone, Pixel"),
]
POOLED = [  # many clips together
    ("Ego4D, 24 clips, laptop copy of the pipeline", 1878, 177 * 60, "docs/results/2026-10-20-ego4d-baseline.md line 15"),
    ("Ego4D, the 4 clips above on the Pixel", 372, 27.8 * 60, "docs/results/2026-10-20-ego4d-baseline.md line 99"),
]
NOT_CAMERA = [  # shown for range only: not what a person records with a camera
    ("feature film, 55 min (Infinix)", 831, 9904 / 3, "docs/results/2026-11-09-storage-and-crash.md (831 kept of 9,904 frames)"),
    ("5-min piece of that film (Infinix, EYKO-44)", 51, 300, "docs/results/2026-11-12-eyko44-workmanager-phone-checks.md"),
    ("screen recording, 60.1 min (Infinix)", 21, 60.1 * 60, "docs/results/2026-11-09-storage-and-crash.md (21 kept frames)"),
]
EXCLUDED = [("EYKO-85 8-min loop of kit clip 1", 14, 480,
             "docs/results/2026-11-15-eyko85-background-long-clip.md: the same 75 s looped, so dedup drops the repeats")]

# Step 2. Minutes recorded per day (sources.md has the quotes and whether each page was opened).
SCENARIOS = [  # key, label, minutes per day, how it is derived
    ("light", "phone camera user", 28 * 47 / 60 / DAYS_PER_MONTH,
     "28 videos a month x 47 s each (IJHCI 2026, smartphone video study)"),
    ("typical", "first-person recording, part of the day", 3.25 * 60,
     "3.25 h a day: median of measured daily wear of personal cameras (2.8 h, 3.25 h, 5.9 h)"),
    ("heavy", "first-person recording, all waking hours", 12 * 60,
     "12 h a day: NTCIR lifeloggers wore the camera 12-14 h a day (lower end)"),
]
OLD_ASSUMPTION = ("Head 2 until now: 1 h/day, 13.4 kept/min (no source)", 60, 13.4)

# Step 4. Measured search time of the app's setup (MAPPED_NATIVE, image table), on battery (EYKO-111).
SEARCH_MS = {  # rows -> ms; docs/results/vectors/offheap/*eyko111-hot2* and *eyko111-lowbat-nosaver*
    "Samsung A32, hot, battery": {20_000: 21.2, 50_000: 51.9, 100_000: 112.1},
    "Pixel 9 Pro XL, 26 % battery": {20_000: 3.2, 50_000: 8.1, 100_000: 13.8},
}
LINES = [  # rows, label, source
    (30_000, "background kill line: 30k-40k rows x 3 tables (Infinix)", "docs/results/2026-11-09-background-kill-mapped-native.md"),
    (100_000, "largest size with a phone search time", "EYKO-111"),
    (300_000, "ADR 0001 trigger 3 (reopen the decision)", "docs/adr/0001-vector-storage.md"),
]
MONTHS = [1, 3, 6, 12]

# Storage, app data only (EYKO-126: the video itself is read from the gallery, not copied). Bytes, decimal units.
# Corrected 25 Nov: database rows are counted at their size ON DISK with SQLite's 4 KB pages (EYKO-167 dbstat), and the
# kept frame's files at what the camera clip's video folder measured (EYKO-126); see the result file, "Step 3b".
AUDIO_PER_MIN = 16_000 * 2 * 60  # 16 kHz 16-bit mono WAV, kept after processing (2026-11-09-storage-and-crash.md)
FRAME_ROW = 202  # one `frames` row on disk (EYKO-167, dbstat at 4 KB pages; 100 B of data); 3 a second
DB_PER_KEPT = 4_106 + 2_053 + 168 + 457  # image_vec, text_vec, video_texts + keyword index, scene_records (EYKO-167, 4 KB)
SIGHTING = 4_119  # one object_sightings row on disk: its 2 KB crop vector fills a 4 KB page (EYKO-167)
SIGHTINGS_PER_KEPT = {"low": 1.93, "central": 5.4, "high": 8.4}  # movie 1,604/831; kit clip 1 54/10; kit clip 2 134/16
FOLDER_PER_KEPT = {  # the kept frame's files in the video folder: its JPEG and its share of the dedup vector file
    "low": (27_500_000 + 1_900_000) / 831,  # movie (1920x804 film): 27.5 MB pictures + 1.9 MB other folder files, 831 kept
    "central": (10_448_896 - round(297.8 * 32_000)) / 13,  # camera clip t4 (EYKO-126): folder minus its WAV, 13 kept
    "high": (10_448_896 - round(297.8 * 32_000)) / 13,
}
SEARCH_COPY = 512 * 4 + 8  # the `.vec` file next to the database: one float32 image vector + its id (ADR 0001)
CHECK = ("EYKO-116 movie run: database grew 14.6 MB for 831 kept frames, 1,604 sightings, 9,904 frame rows",
         831, 1_604, 9_904, 14_600_000)  # 2026-11-09-storage-and-crash.md, Part 2 (a)


def storage_per_day(minutes, kept_per_day, case="central"):
    """Bytes a day by part; `case` picks the low / central / high sightings and folder size per kept frame."""
    return {"audio": minutes * AUDIO_PER_MIN, "frame_rows": minutes * 180 * FRAME_ROW,
            "kept_frame_files": kept_per_day * FOLDER_PER_KEPT[case],
            "database_rows": kept_per_day * (DB_PER_KEPT + SIGHTINGS_PER_KEPT[case] * SIGHTING),
            "search_copy": kept_per_day * SEARCH_COPY}


def rate(rows):
    return [(name, kept / sec * 60, src) for name, kept, sec, src in rows]


def days_to(target, per_day):
    return target / per_day if per_day > 0 else float("inf")


def ms_at(rows, points):
    """Linear from the measured sizes (search time grows in step with the rows: 20k-100k measured)."""
    per_row = statistics.median(ms / n for n, ms in points.items())
    return rows * per_row


def main():
    OUT.mkdir(exist_ok=True)
    camera = rate(CAMERA_CLIPS)
    per_clip = [r for _, r, _ in camera]
    central = POOLED[0][1] / POOLED[0][2] * 60  # largest first-person sample
    low, high = min(per_clip), max(per_clip)
    result = {"kept_per_min": {"camera_clips": camera, "pooled": rate(POOLED), "not_camera": rate(NOT_CAMERA),
                               "excluded": rate(EXCLUDED), "used": {"central": central, "low": low, "high": high,
                                                                    "median_of_clips": statistics.median(per_clip)}},
              "scenarios": [], "search_ms_measured": SEARCH_MS, "lines": LINES}
    rows_csv = []
    for key, label, minutes, how in SCENARIOS:
        per_day = minutes * central
        s = {"key": key, "label": label, "minutes_per_day": minutes, "how": how, "vectors_per_day": per_day,
             "vectors_per_day_range": [minutes * low, minutes * high],
             "months": {m: round(per_day * m * DAYS_PER_MONTH) for m in MONTHS},
             "months_range": {m: [round(minutes * low * m * DAYS_PER_MONTH), round(minutes * high * m * DAYS_PER_MONTH)] for m in MONTHS},
             "days_to": {t: round(days_to(t, per_day), 1) for t, _, _ in LINES},
             "days_to_fastest": {t: round(days_to(t, minutes * high), 1) for t, _, _ in LINES},
             "search_ms_at_12_months": {p: round(ms_at(per_day * 12 * DAYS_PER_MONTH, pts)) for p, pts in SEARCH_MS.items()}}
        parts = storage_per_day(minutes, per_day)
        day_bytes = sum(parts.values())
        low_bytes = sum(storage_per_day(minutes, minutes * low, "low").values())
        high_bytes = sum(storage_per_day(minutes, minutes * high, "high").values())
        s["storage"] = {"mb_per_day": round(day_bytes / 1e6, 2), "mb_per_day_parts": {k: round(v / 1e6, 2) for k, v in parts.items()},
                        "gb": {m: round(day_bytes * m * DAYS_PER_MONTH / 1e9, 2) for m in MONTHS},
                        "gb_range": {m: [round(low_bytes * m * DAYS_PER_MONTH / 1e9, 2), round(high_bytes * m * DAYS_PER_MONTH / 1e9, 2)] for m in MONTHS},
                        "gb_without_audio": {m: round((day_bytes - parts["audio"]) * m * DAYS_PER_MONTH / 1e9, 2) for m in MONTHS},
                        "audio_share": round(parts["audio"] / day_bytes, 3)}
        result["scenarios"].append(s)
        for month in range(13):
            days = month * DAYS_PER_MONTH
            rows_csv.append([key, month, round(per_day * days), round(minutes * low * days), round(minutes * high * days),
                             round(day_bytes * days / 1e9, 3), round((day_bytes - parts["audio"]) * days / 1e9, 3)])
    label, minutes, old_rate = OLD_ASSUMPTION
    result["old_assumption"] = {"label": label, "vectors_per_day": minutes * old_rate,
                                "months": {m: round(minutes * old_rate * m * DAYS_PER_MONTH) for m in MONTHS}}
    with open(OUT / "vector-growth.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "month", "image_vectors_central", "image_vectors_low", "image_vectors_high", "storage_gb",
                    "storage_gb_without_audio"])
        w.writerows(rows_csv)
    name, kept, sightings, frame_rows, measured = CHECK
    predicted = kept * DB_PER_KEPT + sightings * SIGHTING + frame_rows * FRAME_ROW
    result["storage_check"] = {"case": name, "predicted_bytes": round(predicted), "measured_bytes": measured,
                               "error_pct": round((predicted - measured) / measured * 100, 2)}
    result["storage_inputs"] = {"audio_per_min": AUDIO_PER_MIN, "frame_row": FRAME_ROW, "db_per_kept": DB_PER_KEPT, "sighting": SIGHTING,
                                "sightings_per_kept": SIGHTINGS_PER_KEPT, "folder_per_kept": FOLDER_PER_KEPT, "search_copy": SEARCH_COPY,
                                "kept_frame_total": {c: round(FOLDER_PER_KEPT[c] + DB_PER_KEPT + SIGHTINGS_PER_KEPT[c] * SIGHTING + SEARCH_COPY)
                                                     for c in ("low", "central", "high")}}
    (OUT / "vector-growth.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    plot(result, low, high, central)
    plot_storage(result)
    print_summary(result)


def plot(result, low, high, central):
    INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
    colours = {"light": "#1baf7a", "typical": "#2a78d6", "heavy": "#eb6834"}
    fig, ax = plt.subplots(figsize=(9, 4.8))
    months = [d / DAYS_PER_MONTH for d in range(1, 366)]  # day by day from day 1 (a log axis has no 0)
    for s in result["scenarios"]:
        c = colours[s["key"]]
        per_day, (lo, hi) = s["vectors_per_day"], s["vectors_per_day_range"]
        ax.fill_between(months, [lo * m * DAYS_PER_MONTH for m in months], [hi * m * DAYS_PER_MONTH for m in months],
                        color=c, alpha=0.13, linewidth=0)
        mins = s["minutes_per_day"]
        amount = f"{mins:.2f} min/day" if mins < 60 else f"{mins / 60:g} h/day"
        ax.plot(months, [per_day * m * DAYS_PER_MONTH for m in months], color=c, linewidth=2.2, label=f"{s['label']}: {amount}", zorder=4)
        end = per_day * 12 * DAYS_PER_MONTH
        ax.annotate(f"{end:,.0f}", (12, end), xytext=(4, 0), textcoords="offset points", va="center", fontsize=7.5, color=c)
    old = result["old_assumption"]
    ax.plot(months, [old["vectors_per_day"] * m * DAYS_PER_MONTH for m in months], color=MUTED, linewidth=1.2,
            linestyle=(0, (4, 3)), label="Head 2 until now: 1 h/day (no source)")
    for rows, text, _ in LINES:
        ax.axhline(rows, color=INK, linewidth=0.7, linestyle=(0, (2, 2)))
        ax.annotate(text, (9.3, rows), xytext=(0, 3), textcoords="offset points", fontsize=7, color=INK, ha="center",
                    bbox=dict(boxstyle="round,pad=0.15", facecolor=SURFACE, edgecolor="none", alpha=0.9), zorder=2)
    ax.set_yscale("log")
    ax.set_ylim(5, 5e6)
    ax.set_xlim(0, 13.2)
    ax.set_xticks([0, 1, 3, 6, 9, 12])
    ax.set_xlabel("months of use", color=MUTED, fontsize=8)
    ax.set_ylabel("image vectors in the table (log)", color=MUTED, fontsize=8)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=7.5)
    ax.legend(fontsize=7.5, frameon=False, loc="lower right")
    fig.text(0.01, 0.985, "How many image vectors a user has over 12 months (EYKO-101)", ha="left", va="top", fontsize=11,
             color=INK, fontweight="bold")
    fig.text(0.01, 0.93, f"Line: kept frames at {central:.1f} a minute (24 Ego4D clips); band: {low:.1f} to {high:.1f} a minute "
             "(slowest and fastest of our 6 real camera clips). Minutes a day from published studies "
             "(docs/results/vector-growth/sources.md).", ha="left", va="top", fontsize=8, color=MUTED, wrap=True)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    for ext in ("png", "svg"):
        fig.savefig(OUT / f"vector-growth.{ext}", dpi=170, facecolor=SURFACE)
    plt.close(fig)


def plot_storage(result):
    INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
    colours = {"light": "#1baf7a", "typical": "#2a78d6", "heavy": "#eb6834"}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
    days = list(range(1, 366))
    months = [d / DAYS_PER_MONTH for d in days]
    for ax, title, audio in ((axes[0], "As built: the 16 kHz audio file is kept", True),
                             (axes[1], "If the audio file is deleted after processing", False)):
        for s in result["scenarios"]:
            c, st = colours[s["key"]], s["storage"]
            per_day = (st["mb_per_day"] - (0 if audio else st["mb_per_day_parts"]["audio"])) / 1e3
            at12 = st["gb"][12] if audio else st["gb_without_audio"][12]
            ax.plot(months, [per_day * d for d in days], color=c, linewidth=2.2,
                    label=f"{s['label']}: {per_day * 1e3:,.0f} MB/day")
            ax.annotate(f"{at12:,.1f} GB", (12, at12), xytext=(4, 0), textcoords="offset points", va="center", fontsize=7.5, color=c)
        ax.set_title(title, fontsize=9, color=INK, loc="left")
        ax.set_yscale("log")
        ax.set_ylim(1e-3, 2e3)
        ax.set_xlim(0, 14)
        ax.set_xticks([0, 1, 3, 6, 9, 12])
        ax.set_xlabel("months of use", color=MUTED, fontsize=8)
        ax.grid(True, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.set_facecolor(SURFACE)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.tick_params(colors=MUTED, labelsize=7.5)
        ax.legend(fontsize=7.5, frameon=False, loc="lower right")
    axes[0].set_ylabel("app storage, GB (log)", color=MUTED, fontsize=8)
    chk = result["storage_check"]
    fig.text(0.01, 0.985, "How much phone storage the app uses over 12 months (EYKO-101)", ha="left", va="top", fontsize=11,
             color=INK, fontweight="bold")
    tot = result["storage_inputs"]["kept_frame_total"]["central"] / 1e3
    fig.text(0.01, 0.93, "Video is read from the gallery (not copied). Per minute of video: 1.92 MB of 16 kHz audio + 36 kB of frame "
             f"rows; per kept frame: {tot:.0f} kB (JPEG, database rows on disk with 4 KB pages incl. 5.4 sightings, search copy). "
             f"Database part checked on a measured run: {chk['error_pct']:+.1f} %. Sources: docs/results/2026-11-21-vector-growth-estimate.md.",
             ha="left", va="top", fontsize=8, color=MUTED, wrap=True)
    fig.tight_layout(rect=(0, 0, 1, 0.87))
    for ext in ("png", "svg"):
        fig.savefig(OUT / f"vector-growth-storage.{ext}", dpi=170, facecolor=SURFACE)
    plt.close(fig)


def print_summary(result):
    u = result["kept_per_min"]["used"]
    print(f"kept/min: central {u['central']:.2f}, clips {u['low']:.2f}-{u['high']:.2f}, median of clips {u['median_of_clips']:.2f}")
    for s in result["scenarios"]:
        print(f"{s['key']:8} {s['minutes_per_day']:7.2f} min/day -> {s['vectors_per_day']:8.0f}/day; months {s['months']}; "
              f"days to {s['days_to']}; fastest {s['days_to_fastest']}; ms at 12 mo {s['search_ms_at_12_months']}")
    print("old assumption", result["old_assumption"])
    print("storage check", result["storage_check"])
    for s in result["scenarios"]:
        print(f"{s['key']:8} storage {s['storage']}")


if __name__ == "__main__":
    main()
