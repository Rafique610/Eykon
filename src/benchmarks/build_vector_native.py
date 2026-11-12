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
    tools = ap.parse_args().ndk / "toolchains/llvm/prebuilt/windows-x86_64/bin"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(tools / "clang.exe"), "--target=aarch64-linux-android31", "-O3", "-ffp-contract=off", "-fPIC", "-shared",
           "-Wall", "-Wextra", "-Wl,-z,max-page-size=16384", "-Wl,-z,common-page-size=16384", str(SRC), "-o", str(OUT)]
    print("$ " + " ".join(cmd))
    subprocess.run(cmd, check=True)
    loads = [l for l in subprocess.run([str(tools / "llvm-readelf.exe"), "-lW", str(OUT)], capture_output=True, text=True,
                                       check=True).stdout.splitlines() if l.strip().startswith("LOAD")]
    aligned = all(l.split()[-1] == "0x4000" for l in loads)
    syms = subprocess.run([str(tools / "llvm-readelf.exe"), "-sW", "--dyn-syms", str(OUT)], capture_output=True, text=True).stdout
    exported = bool(re.search(r"Java_com_eykon_memory_video_VectorNative_scoreF32", syms))
    print(f"{OUT.stat().st_size} B  sha256 {hashlib.sha256(OUT.read_bytes()).hexdigest()}  "
          f"LOAD 16 KB aligned: {aligned} ({len(loads)} segments)  JNI symbol exported: {exported}")
    if not (aligned and exported):
        sys.exit("check failed")


if __name__ == "__main__":
    main()
