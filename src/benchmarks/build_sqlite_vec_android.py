"""EYKO-104 (route R5): build our own sqlite-vec libvec0.so for Android and check it.

Builds sqlite-vec v0.1.9 for arm64-v8a twice (with and without NEON) with the NDK
clang, 16 KB page aligned, then saves the raw readelf output and SHA256 sums so the
route cards (EYKO-105..107) load a file we built and checked ourselves.

    task build-sqlite-vec-android                     # NDK in D:/eykon-cache/ndk
    task build-sqlite-vec-android -- --ndk <ndk dir>  # any NDK r28+

Binaries stay out of git (CACHE/out); the evidence folder is committed.
"""

import argparse
import hashlib
import re
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

CACHE = Path("D:/eykon-cache/sqlite-vec-android")
DEFAULT_NDK = Path("D:/eykon-cache/ndk/android-ndk-r28c")
EVIDENCE = Path("docs/results/2026-11-07-sqlite-vec-android-build")
API = 31  # the app's minSdk

# Pinned sources: (url, hash name, digest). sqlite.org publishes SHA3-256.
VEC_TGZ = (
    "https://github.com/asg017/sqlite-vec/releases/download/v0.1.9/sqlite-vec-0.1.9-amalgamation.tar.gz",
    "sha256",
    "3acd67cb4aff080c7050926fd3cf8227905fe5b7ee3829d8ee5024ab1283cf61",
)
SQLITE_ZIP = (
    "https://www.sqlite.org/2026/sqlite-amalgamation-3540100.zip",
    "sha3_256",
    "92281c86e2957f9b9305890f9ac04204caa7b677cc868dc326d942689df28e30",
)
VEC_COMMIT = "e9f598abfa0c06b328d8fe5da9c3760cce74be10"  # tag v0.1.9

# Same flags as sqlite-vec's Makefile "loadable" target, plus the Android target and
# explicit 16 KB pages (r28 already defaults to it; explicit keeps older NDKs honest).
FLAGS = [
    f"--target=aarch64-linux-android{API}",
    "-O3", "-fPIC", "-shared", "-Wall", "-Wextra",
    "-Wl,-z,max-page-size=16384", "-Wl,-z,common-page-size=16384",
]
VARIANTS = {"neon": ["-DSQLITE_VEC_ENABLE_NEON"], "no-neon": []}


def fetch(url: str, algo: str, digest: str) -> Path:
    path = CACHE / "src" / url.rsplit("/", 1)[1]
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, path)
    got = hashlib.new(algo, path.read_bytes()).hexdigest()
    if got != digest:
        sys.exit(f"{path.name}: {algo} {got} != pinned {digest}")
    return path


def unpack() -> tuple[Path, Path]:
    vec_dir, sql_dir = CACHE / "src/v0.1.9", CACHE / "src/sqlite-amalgamation-3540100"
    with tarfile.open(fetch(*VEC_TGZ)) as t:
        t.extractall(vec_dir)  # pinned hash above; two plain files
    with zipfile.ZipFile(fetch(*SQLITE_ZIP)) as z:
        z.extractall(CACHE / "src")
    header = (vec_dir / "sqlite-vec.h").read_text()
    if VEC_COMMIT not in header:
        sys.exit("sqlite-vec.h does not name the pinned v0.1.9 commit")
    return vec_dir, sql_dir


def run(cmd: list) -> str:
    out = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if out.returncode:
        sys.exit(f"failed: {' '.join(map(str, cmd))}\n{out.stdout}{out.stderr}")
    return out.stdout


def check(tools: Path, so: Path, name: str) -> tuple[str, list[str]]:
    """Save raw readelf output; return the SHA256 and the failed checks (empty = pass)."""
    readelf = tools / "llvm-readelf.exe"
    segments = run([readelf, "-lW", so])
    symbols = run([readelf, "-sW", "--dyn-syms", so])
    dynamic = run([readelf, "-dW", so])
    disasm = run([tools / "llvm-objdump.exe", "-d", so])
    sha = hashlib.sha256(so.read_bytes()).hexdigest()
    loads = [l for l in segments.splitlines() if l.strip().startswith("LOAD")]
    needed = re.findall(r"Shared library: \[(.+?)\]", dynamic)
    vector_ops = len(re.findall(r"\bv\d+\.4s\b", disasm))
    (EVIDENCE / f"readelf-{name}.txt").write_text(
        f"# {so}\n# size {so.stat().st_size} bytes, sha256 {sha}\n"
        f"# arm64 4-lane float instructions in the disassembly: {vector_ops}\n\n"
        f"$ llvm-readelf -lW libvec0.so\n{segments}\n"
        f"$ llvm-readelf -dW libvec0.so\n{dynamic}\n"
        f"$ llvm-readelf -sW --dyn-syms libvec0.so | grep sqlite3_vec_init\n"
        + "\n".join(l for l in symbols.splitlines() if "sqlite3_vec_init" in l) + "\n"
    )
    failed = []
    if not loads or any(not l.split()[-1] == "0x4000" for l in loads):
        failed.append("LOAD segments not all aligned 0x4000")
    if not re.search(r"FUNC\s+GLOBAL\s+DEFAULT\s+\d+\s+sqlite3_vec_init$", symbols, re.M):
        failed.append("sqlite3_vec_init not exported")
    if set(needed) - {"libc.so", "libm.so", "libdl.so"}:
        failed.append(f"unexpected NEEDED: {needed}")
    print(f"{name:8} {sha}  {so.stat().st_size:>7} B  vector ops {vector_ops:>4}  "
          f"NEEDED {needed}  {'PASS' if not failed else 'FAIL: ' + '; '.join(failed)}")
    return sha, [f"{name}: {f}" for f in failed]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ndk", type=Path, default=DEFAULT_NDK)
    ndk = ap.parse_args().ndk
    tools = ndk / "toolchains/llvm/prebuilt/windows-x86_64/bin"
    clang = tools / "clang.exe"
    if not clang.exists():
        sys.exit(f"no NDK clang at {clang} (install NDK r28+ or pass --ndk)")
    vec_dir, sql_dir = unpack()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    ndk_rev = re.search(r"Pkg.Revision\s*=\s*(\S+)", (ndk / "source.properties").read_text())[1]
    lines, failed = [f"# NDK {ndk_rev}, sqlite-vec v0.1.9 {VEC_COMMIT}, SQLite headers 3.54.1"], []
    for name, extra in VARIANTS.items():
        so = CACHE / "out" / name / "arm64-v8a" / "libvec0.so"
        so.parent.mkdir(parents=True, exist_ok=True)
        cmd = [clang, *FLAGS, *extra, f"-I{sql_dir}", vec_dir / "sqlite-vec.c", "-lm", "-o", so]
        lines.append("$ " + " ".join(str(c) for c in cmd))
        run(cmd)
        # the _neon functions get inlined (no symbol), so prove the path from the preprocessor
        pre = run([clang, f"--target=aarch64-linux-android{API}", "-E", *extra,
                   f"-I{sql_dir}", vec_dir / "sqlite-vec.c"])
        neon_calls = len(re.findall(r"\w+_neon\(", pre))
        lines.append(f"# {name}: NEON function calls in the preprocessed source: {neon_calls}")
        if (neon_calls > 0) != bool(extra):
            failed.append(f"{name}: NEON path {'missing' if extra else 'present'}")
        sha, bad = check(tools, so, name)
        lines.append(f"{sha}  {name}/arm64-v8a/libvec0.so")
        failed += bad
    (EVIDENCE / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n")
    if failed:
        sys.exit("\n".join(failed))


if __name__ == "__main__":
    main()
