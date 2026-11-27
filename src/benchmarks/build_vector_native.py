"""EYKO-114: build libeykonvec.so (NEON dot products over the mapped vector file) for arm64 phones.

    task build-vector-native                     # NDK in D:/eykon-cache/ndk
    task build-vector-native -- --ndk <ndk dir>

Writes android/app/src/main/jniLibs/arm64-v8a/libeykonvec.so (git-ignored) and prints the readelf
16 KB check and SHA256. -ffp-contract=off keeps multiply and add separate, so the scores stay
bit-identical to VideoVectors.dot().
"""

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "android/app/src/main/cpp/eykonvec.c"
OUT = ROOT / "android/app/src/main/jniLibs/arm64-v8a/libeykonvec.so"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ndk", type=Path, default=Path("D:/eykon-cache/ndk/android-ndk-r28c"))
    # Windows (the team's laptops) or Linux/macOS: the NDK's prebuilt folder and file names differ
    host, exe = ("windows-x86_64", ".exe") if sys.platform == "win32" else (("darwin-x86_64" if sys.platform == "darwin" else "linux-x86_64"), "")
    tools = ap.parse_args().ndk / f"toolchains/llvm/prebuilt/{host}/bin"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(tools / f"clang{exe}"), "--target=aarch64-linux-android31", "-O3", "-ffp-contract=off", "-fPIC", "-shared",
           "-Wall", "-Wextra", "-Wl,-z,max-page-size=16384", "-Wl,-z,common-page-size=16384", str(SRC), "-o", str(OUT)]
    print("$ " + " ".join(cmd))
    subprocess.run(cmd, check=True)
    loads = [l for l in subprocess.run([str(tools / f"llvm-readelf{exe}"), "-lW", str(OUT)], capture_output=True, text=True,
                                       check=True).stdout.splitlines() if l.strip().startswith("LOAD")]
    aligned = all(l.split()[-1] == "0x4000" for l in loads)
    syms = subprocess.run([str(tools / f"llvm-readelf{exe}"), "-sW", "--dyn-syms", str(OUT)], capture_output=True, text=True).stdout
    exported = all(re.search(rf"Java_com_eykon_memory_video_VectorNative_{f}\b", syms) for f in ("scoreF32",))
    print(f"{OUT.stat().st_size} B  sha256 {hashlib.sha256(OUT.read_bytes()).hexdigest()}  "
          f"LOAD 16 KB aligned: {aligned} ({len(loads)} segments)  JNI symbol exported: {exported}")
    if not (aligned and exported):
        sys.exit("check failed")


if __name__ == "__main__":
    main()
