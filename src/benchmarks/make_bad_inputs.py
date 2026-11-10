"""EYKO-118: make a small set of awkward video files from ONE kit clip, with ffmpeg, and check each file is what its name says.

Usage:   uv run python src/benchmarks/make_bad_inputs.py --src <kit clip>.mp4 [--out data/bad-inputs] [--skip-big]
Output:  data/bad-inputs/B1 ... B12 files plus MANIFEST.csv (git-ignored: the script is what we commit, not the files).

Files (10 to 20 s each, cut from the kit clip; B12 is long on purpose):
  B1 H.264 baseline (control)   B2 HEVC 8-bit            B3 HEVC 10-bit tagged as HDR (tags only: the source is SDR)
  B4 portrait (rotation 90 in metadata)                    B5 variable frame rate
  B6 metadata stripped (no recording time, no GPS)         B7 truncated (last 30 % of the bytes cut off)
  B8 audio-only .mp4                                       B9 video with no audio track
  B10a .mov, B10b .m4v, B10c .avi (three of the four types the app accepts; the fourth, .mp4, is B1)
  B11 .mkv (should be refused)                             B12 just over the app's 500 MB limit (the clip looped, stream copy)

The app's rules, read from the code: types mp4, mov, m4v, avi (by MIME type); limit 500 MB = 500 * 1024 * 1024 bytes
(`VideoMetadata.MAX_MB`, `VideoCapture.copy`). Needs ffmpeg and ffprobe (on PATH, or pass --ffmpeg-dir).
"""
import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

LIMIT = 500 * 1024 * 1024
START_S, LENGTH_S = 10, 15


def find_tool(name: str, directory: str | None) -> str:
    if directory:
        return str(Path(directory) / f"{name}.exe") if (Path(directory) / f"{name}.exe").exists() else str(Path(directory) / name)
    found = shutil.which(name)
    if not found:
        sys.exit(f"{name} not found: put it on PATH or pass --ffmpeg-dir")
    return found


def probe(ffprobe: str, path: Path) -> dict | None:
    r = subprocess.run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="one kit clip (for example PXL_20261014_094359202.mp4)")
    ap.add_argument("--out", default="data/bad-inputs")
    ap.add_argument("--ffmpeg-dir", help="folder with ffmpeg and ffprobe if they are not on PATH")
    ap.add_argument("--skip-big", action="store_true", help="skip B12 (a file of about 530 MB)")
    a = ap.parse_args()
    ffmpeg, ffprobe = find_tool("ffmpeg", a.ffmpeg_dir), find_tool("ffprobe", a.ffmpeg_dir)
    src = Path(a.src)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cut_plain = ["-ss", str(START_S), "-t", str(LENGTH_S), "-i", str(src)]
    # ffmpeg does not carry the clip's recording time over by itself; set it, so that B6 (stripped) differs from the others
    src_info = probe(ffprobe, src) or {}
    recorded = next((st["tags"]["creation_time"] for st in src_info.get("streams", []) if "creation_time" in st.get("tags", {})), "")
    cut = [*cut_plain, *(["-metadata", f"creation_time={recorded}"] if recorded else [])]
    # The Pixel clip is full-range (yuvj420p); convert to the usual limited range so the control file is an ordinary one
    rng = "scale=in_range=pc:out_range=tv"
    h264 = ["-vf", rng, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p"]
    aac = ["-c:a", "aac", "-b:a", "128k"]
    bitexact = ["-fflags", "+bitexact", "-flags:v", "+bitexact", "-flags:a", "+bitexact"]

    def run(name: str, args: list[str]) -> Path:
        target = out / name
        cmd = [ffmpeg, "-y", "-v", "error", *args, str(target)]
        print("  ffmpeg", " ".join(cmd[4:-1]), "->", target.name)
        subprocess.run(cmd, check=True)
        return target

    made: dict[str, Path] = {}
    made["B1"] = run("B1_h264_baseline.mp4", [*cut, *h264, "-profile:v", "baseline", "-level", "4.0", *aac])
    made["B2"] = run("B2_hevc_8bit.mp4", [*cut, "-vf", rng, "-c:v", "libx265", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p", "-tag:v", "hvc1", *aac])
    made["B3"] = run("B3_hevc_10bit_hdr_tagged.mp4", [*cut, "-vf", rng + ",setparams=color_primaries=bt2020:color_trc=smpte2084:colorspace=bt2020nc", "-c:v", "libx265", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p10le", "-tag:v", "hvc1",
                                                         "-color_primaries", "bt2020", "-color_trc", "smpte2084", "-colorspace", "bt2020nc",
                                                         "-x265-params", "colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc", *aac])
    # B4: encode as usual, then copy the streams with a rotation of 90 degrees in the metadata only (no pixels turned)
    plain = run("_B4_plain.mp4", [*cut, *h264, *aac])
    made["B4"] = run("B4_portrait_rotation90.mp4", ["-display_rotation:v", "90", "-i", str(plain), "-c", "copy", *(["-metadata", f"creation_time={recorded}"] if recorded else [])])
    plain.unlink()
    made["B5"] = run("B5_variable_frame_rate.mp4", [*cut, "-fps_mode", "vfr", *h264[2:], "-vf", f"select='not(eq(mod(n,3),1))*not(eq(mod(n,7),3))',{rng}", *aac])
    made["B6"] = run("B6_metadata_stripped.mp4", [*cut_plain, "-map_metadata", "-1", "-map_chapters", "-1", *bitexact, *h264, *aac])
    # B7: the control file written the usual way (no faststart: the index is at the END), then the last 30 % of the bytes cut off
    data = made["B1"].read_bytes()
    made["B7"] = out / "B7_truncated.mp4"
    made["B7"].write_bytes(data[: int(len(data) * 0.7)])
    print("  truncated copy of B1 ->", made["B7"].name)
    made["B8"] = run("B8_audio_only.mp4", [*cut, "-vn", *aac])
    made["B9"] = run("B9_no_audio.mp4", [*cut, "-an", *h264])
    made["B10a"] = run("B10a_h264.mov", [*cut, *h264, *aac, "-f", "mov"])
    made["B10b"] = run("B10b_h264.m4v", [*cut, *h264, *aac, "-f", "ipod"])
    made["B10c"] = run("B10c_mpeg4_mp3.avi", [*cut, "-c:v", "mpeg4", "-q:v", "5", "-c:a", "libmp3lame", "-b:a", "128k", "-f", "avi"])
    made["B11"] = run("B11_h264.mkv", [*cut, *h264, *aac, "-f", "matroska"])
    if not a.skip_big:
        size, duration = src.stat().st_size, float(probe(ffprobe, src)["format"]["duration"])
        seconds = 530_000_000 / (size / duration)  # aim at about 530 MB: over 524,288,000 bytes, with room either side
        made["B12"] = out / "B12_over_500MB.mp4"
        print(f"  looping the clip for {seconds:.1f} s (stream copy) -> {made['B12'].name}")
        subprocess.run([ffmpeg, "-y", "-v", "error", "-stream_loop", "-1", "-i", str(src), "-t", f"{seconds:.2f}", "-c", "copy", str(made["B12"])], check=True)

    rows, problems = [], []
    for key, path in made.items():
        info = probe(ffprobe, path)
        size = path.stat().st_size
        v = next((s for s in (info or {}).get("streams", []) if s["codec_type"] == "video"), None)
        au = next((s for s in (info or {}).get("streams", []) if s["codec_type"] == "audio"), None)
        tags = dict((info or {}).get("format", {}).get("tags", {}))
        for st in (info or {}).get("streams", []):  # a recording time can also sit on a track
            for k, val in st.get("tags", {}).items():
                if k in ("creation_time", "location") and not tags.get(k):
                    tags[k] = val
        rotation = next((int(d["rotation"]) for d in (v or {}).get("side_data_list", []) if "rotation" in d), 0)
        rows.append({
            "id": key, "file": path.name, "bytes": size, "readable_by_ffprobe": info is not None,
            "video_codec": v["codec_name"] if v else "", "pix_fmt": v.get("pix_fmt", "") if v else "",
            "color_transfer": v.get("color_transfer", "") if v else "", "size": f"{v['width']}x{v['height']}" if v else "",
            "rotation": rotation, "r_frame_rate": v.get("r_frame_rate", "") if v else "", "avg_frame_rate": v.get("avg_frame_rate", "") if v else "",
            "audio": au["codec_name"] if au else "", "duration_s": (info or {}).get("format", {}).get("duration", ""),
            "creation_time": tags.get("creation_time", ""), "location": tags.get("location", ""),
        })

    def expect(key: str, ok: bool, why: str) -> None:
        if not ok:
            problems.append(f"{key}: {why}")

    by = {r["id"]: r for r in rows}
    expect("B1", by["B1"]["video_codec"] == "h264", "not H.264")
    expect("B2", by["B2"]["video_codec"] == "hevc" and by["B2"]["pix_fmt"] == "yuv420p", "not HEVC 8-bit")
    expect("B3", by["B3"]["video_codec"] == "hevc" and "10" in by["B3"]["pix_fmt"] and by["B3"]["color_transfer"] == "smpte2084", "not HEVC 10-bit with the HDR transfer tag")
    expect("B4", abs(by["B4"]["rotation"]) == 90, f"rotation is {by['B4']['rotation']}, expected 90")
    expect("B5", by["B5"]["r_frame_rate"] != by["B5"]["avg_frame_rate"], "frame rate is constant")
    expect("B1", bool(by["B1"]["location"]) and bool(by["B1"]["creation_time"]), "the control has no recording time or location, so B6 would prove nothing")
    expect("B6", not by["B6"]["location"] and (not by["B6"]["creation_time"] or by["B6"]["creation_time"].startswith("1904")), "still has a recording time or location")
    expect("B7", not by["B7"]["readable_by_ffprobe"], "the truncated file can still be read")
    expect("B8", by["B8"]["video_codec"] == "" and by["B8"]["audio"] != "", "not audio-only")
    expect("B9", by["B9"]["audio"] == "" and by["B9"]["video_codec"] != "", "still has audio")
    expect("B10a", by["B10a"]["readable_by_ffprobe"] and path_suffix(by["B10a"]) == ".mov", "bad .mov")
    expect("B10b", by["B10b"]["readable_by_ffprobe"] and path_suffix(by["B10b"]) == ".m4v", "bad .m4v")
    expect("B10c", by["B10c"]["readable_by_ffprobe"] and path_suffix(by["B10c"]) == ".avi", "bad .avi")
    expect("B11", by["B11"]["readable_by_ffprobe"] and path_suffix(by["B11"]) == ".mkv", "bad .mkv")
    if "B12" in by:
        expect("B12", LIMIT < by["B12"]["bytes"] < LIMIT * 1.05, f"{by['B12']['bytes']} bytes is not just over {LIMIT}")
    for key in ("B1", "B2", "B3", "B4", "B5", "B6", "B8", "B9", "B10a", "B10b", "B10c", "B11"):
        d = float(by[key]["duration_s"] or 0)
        expect(key, 5 <= d <= 21, f"duration {d:.1f} s is not 10 to 20 s")

    with open(out / "MANIFEST.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print()
    for r in rows:
        print(f"{r['id']:5} {r['file']:32} {r['bytes'] / 1e6:8.1f} MB  {r['video_codec'] or '-':6} {r['pix_fmt'] or '-':10} rot={r['rotation']:<3} audio={r['audio'] or '-':6} readable={r['readable_by_ffprobe']}")
    if problems:
        print("\nPROBLEMS:", *problems, sep="\n  ")
        return 1
    print(f"\nall {len(rows)} files are what their names say. Manifest: {out / 'MANIFEST.csv'}")
    return 0


def path_suffix(row: dict) -> str:
    return Path(row["file"]).suffix


if __name__ == "__main__":
    sys.exit(main())
