"""Golden numbers for the cheap frame filters (card EYKO-5). Run: task golden-filters

Makes four small test pictures and computes, with OpenCV, the exact measures the phone must
reproduce: brightness, variance of the Laplacian (Pech-Pacheco et al., ICPR 2000), mean absolute
difference and histogram change. The phone's Kotlin code is tested against this file.
"""
import json
import subprocess
from pathlib import Path

import cv2
import imageio_ffmpeg
import numpy as np

OUT = Path("android/app/src/test/resources/filters")
SMALL_SIDE = 320  # the longer side after shrinking by a whole-number factor
PICTURES = {  # name -> ffmpeg picture source and filter
    "sharp": ("testsrc2=size=640x360:rate=1", "null"),
    "other": ("mandelbrot=size=640x360:rate=1", "null"),
    "blurred": ("testsrc2=size=640x360:rate=1", "gblur=sigma=6"),
    "dark": ("testsrc2=size=640x360:rate=1", "eq=brightness=-0.85"),
    "upright": ("testsrc2=size=360x640:rate=1", "null"),
}


def small_gray(path: Path) -> np.ndarray:
    """Gray picture shrunk by a whole-number factor so its longer side is about SMALL_SIDE."""
    gray = cv2.cvtColor(cv2.imread(str(path), cv2.IMREAD_COLOR), cv2.COLOR_BGR2GRAY)
    k = max(1, round(max(gray.shape) / SMALL_SIDE))
    h, w = gray.shape[0] // k, gray.shape[1] // k
    return cv2.resize(gray[: h * k, : w * k], (w, h), interpolation=cv2.INTER_AREA)


def hist(gray: np.ndarray) -> np.ndarray:
    return cv2.calcHist([gray], [0], None, [64], [0, 256])


def measures(gray: np.ndarray) -> dict:
    return {
        "width": int(gray.shape[1]),
        "height": int(gray.shape[0]),
        "brightness": float(gray.mean()),
        "laplacian_variance": float(cv2.Laplacian(gray, cv2.CV_64F).var()),
        "checksum": int(gray.astype(np.int64).sum()),
    }


def pair(a: np.ndarray, b: np.ndarray) -> dict:
    return {
        "diff": float(cv2.absdiff(a, b).mean()),
        "hist_change": float(cv2.compareHist(hist(a), hist(b), cv2.HISTCMP_BHATTACHARYYA)),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    grays = {}
    for name, (source, effect) in PICTURES.items():
        path = OUT / f"{name}.png"
        subprocess.run(
            [ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi", "-i", source, "-vf", effect, "-frames:v", "1", "-ss", "2", str(path)],
            check=True,
        )
        grays[name] = small_gray(path)

    # Which integer formula does this OpenCV use for colour -> gray? The phone copies the one that matches.
    b, g, r = cv2.split(cv2.imread(str(OUT / "sharp.png"), cv2.IMREAD_COLOR).astype(np.int64))
    real = cv2.cvtColor(cv2.imread(str(OUT / "sharp.png"), cv2.IMREAD_COLOR), cv2.COLOR_BGR2GRAY).astype(np.int64)
    for label, mine in {
        "(r*4899 + g*9617 + b*1868 + 8192) >> 14": (r * 4899 + g * 9617 + b * 1868 + 8192) >> 14,
        "(r*9798 + g*19235 + b*3735 + 16384) >> 15": (r * 9798 + g * 19235 + b * 3735 + 16384) >> 15,
    }.items():
        print(f"gray formula {label}: largest difference from OpenCV = {int(np.abs(mine - real).max())}")

    golden = {
        "opencv": cv2.__version__,
        "pictures": {name: measures(gray) for name, gray in grays.items()},
        "pairs": {
            "sharp_vs_sharp": pair(grays["sharp"], grays["sharp"]),
            "sharp_vs_other": pair(grays["sharp"], grays["other"]),
            "sharp_vs_blurred": pair(grays["sharp"], grays["blurred"]),
            "sharp_vs_dark": pair(grays["sharp"], grays["dark"]),
        },
    }
    (OUT / "golden.json").write_text(json.dumps(golden, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(golden, indent=2))


if __name__ == "__main__":
    main()
