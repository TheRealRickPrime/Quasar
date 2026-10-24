"""Linux CI build of pinned official libsodium; no APK keys, patching or device execution."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile
from pathlib import Path

from verify_apk import elf_segments

VERSION = "1.0.22"
SOURCE_URL = f"https://download.libsodium.org/libsodium/releases/libsodium-{VERSION}.tar.gz"
SOURCE_SHA256 = "adbdd8f16149e81ac6078a03aca6fc03b592b89ef7b5ed83841c086191be3349"
SOURCE_COMMIT = "77e1ce5d6dee871c49ef211222ba18ef0c486bda"
BASELINE_URL = "https://repo.maven.apache.org/maven2/com/goterl/lazysodium-android/5.2.0/lazysodium-android-5.2.0.aar"
BASELINE_SHA256 = "b5378c1d9db2573d61b304e89cf83db187a05c3e4ff081d9b2ef3d0bb00ca314"
ABIS = {
    "arm64-v8a": ("aarch64-linux-android", "aarch64-linux-android"),
    "armeabi-v7a": ("arm-linux-androideabi", "armv7a-linux-androideabi"),
    "x86_64": ("x86_64-linux-android", "x86_64-linux-android"),
    "x86": ("i686-linux-android", "i686-linux-android"),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(url: str, path: Path, expected: str) -> None:
    urllib.request.urlretrieve(url, path)
    if digest(path) != expected:
        raise ValueError(f"Official input SHA256 mismatch: {path.name}")


def run(args: list[str], cwd: Path, env: dict | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)
    if result.returncode:
        print(result.stdout[-12000:])
        print(result.stderr[-12000:])
        raise subprocess.CalledProcessError(result.returncode, args)
    return result.stdout


def exports(nm: Path, library: Path) -> set[str]:
    output = subprocess.check_output([str(nm), "-D", "--defined-only", str(library)], text=True)
    return {line.split()[-1].split("@")[0] for line in output.splitlines() if line.split()}


def build(ndk: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    source = out / f"libsodium-{VERSION}.tar.gz"
    baseline = out / "lazysodium-android-5.2.0.aar"
    fetch(SOURCE_URL, source, SOURCE_SHA256)
    fetch(BASELINE_URL, baseline, BASELINE_SHA256)
    toolchain = ndk / "toolchains" / "llvm" / "prebuilt" / "linux-x86_64"
    nm = toolchain / "bin" / "llvm-nm"
    report = {
        "sourceUrl": SOURCE_URL, "sourceSHA256": SOURCE_SHA256, "tag": f"{VERSION}-RELEASE",
        "sourceCommit": SOURCE_COMMIT, "ndk": "28.2.13676358", "api": 26,
        "baselineAarSHA256": BASELINE_SHA256,
        "ldflags": "-Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384 -Wl,-z,relro,-z,now",
        "androidRuntimeTested": False, "libraries": [],
    }
    for abi, target in [("host", None), *ABIS.items()]:
        work = out / f"source-{abi}"
        work.mkdir()
        with tarfile.open(source) as archive:
            archive.extractall(work, filter="data")
        work = work / f"libsodium-{VERSION}"
        install = out / abi
        env = dict(os.environ)
        args = ["./configure", f"--prefix={install}", "--disable-soname-versions",
                "--enable-shared", "--disable-static"]
        if target is not None:
            host, compiler = target
            env.update(CC=str(toolchain / "bin" / f"{compiler}26-clang"),
                       AR=str(toolchain / "bin" / "llvm-ar"),
                       RANLIB=str(toolchain / "bin" / "llvm-ranlib"),
                       STRIP=str(toolchain / "bin" / "llvm-strip"),
                       CFLAGS="-O2 -fPIC", LDFLAGS=report["ldflags"])
            args += [f"--host={host}", "--disable-pie"]
        run(args, work, env)
        run(["make", "-j2"], work, env)
        if abi == "host":
            run(["make", "-j2", "check"], work, env)
        run(["make", "install"], work, env)
        library = install / "lib" / "libsodium.so"
        if abi == "host":
            shutil.copy2(work / "LICENSE", out / "LICENSE")
            continue
        segments = elf_segments(library.read_bytes())
        loads = [s for s in segments if s["type"] == "LOAD"]
        relro = [s for s in segments if s["type"] == "GNU_RELRO"]
        if not loads or not all(s["align"] >= 16384 and
                (s["vaddr"] - s["offset"]) % 16384 == 0 for s in loads):
            raise ValueError(f"{abi}: LOAD alignment is not 16 KB")
        if not relro or not all((s["vaddr"] + s["memSize"]) % 16384 == 0 for s in relro):
            raise ValueError(f"{abi}: GNU_RELRO boundary is not 16 KB")
        old = out / f"baseline-{abi}.so"
        with zipfile.ZipFile(baseline) as archive:
            old.write_bytes(archive.read(f"jni/{abi}/libsodium.so"))
        old_exports, new_exports = exports(nm, old), exports(nm, library)
        missing = old_exports - new_exports
        if missing:
            raise ValueError(f"{abi}: removed baseline exports: {sorted(missing)}")
        destination = out / "jni" / abi / "libsodium.so"
        destination.parent.mkdir(parents=True)
        shutil.copy2(library, destination)
        subprocess.run([str(toolchain / "bin" / "llvm-strip"), "--strip-unneeded", str(destination)], check=True)
        report["libraries"].append({
            "abi": abi, "sha256": digest(destination), "segments": segments,
            "baselineExportCount": len(old_exports), "exportCount": len(new_exports),
            "missingExports": sorted(missing),
        })
    (out / "build-report.json").write_text(json.dumps(report, indent=2) + "\n")
    files = sorted((out / "jni").rglob("*.so"))
    (out / "SHA256SUMS.txt").write_text("".join(f"{digest(p)}  {p.relative_to(out).as_posix()}\n" for p in files))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ndk", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    build(args.ndk.resolve(), args.out.resolve())
