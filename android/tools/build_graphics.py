"""Rebuild only official graphics-path 1.0.1 native code, preserving its Java binding."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tarfile
import urllib.request
import zipfile
from pathlib import Path

from build_sodium import ABIS, digest, exports, fetch, run
from verify_apk import elf_segments

COMMIT = "8a05a22af450d589ef911d772a001a49dcb05b71"
SOURCE_URL = ("https://android.googlesource.com/platform/frameworks/support/+archive/"
              f"{COMMIT}/graphics/graphics-path/src/main/cpp.tar.gz")
SOURCE_FILES = {
    "CMakeLists.txt": "87a8967586e828d2b1cc6c5745d09f30466036bffbcd780b378c75239d90b173",
    "Conic.cpp": "49b3da93aa43480cf9cd481590be48705cb9340c52e5d09635efbd0ece07be83",
    "Conic.h": "cd315ad7c8d030c72e96893e9a0feec463d72d2066209a203dedcf0925398a6f",
    "Path.h": "4ee841338063d8c6f71ff4c655ecf52559f6c6df9af79835388dae1ebcd8b982",
    "PathIterator.cpp": "3705946b43bf894e013f46ccc940f9923f43285340f8fc2128f95c59238ec7f8",
    "PathIterator.h": "a16e99b0273fb7205607eb0cf51fc7be518a55f3446a304f92ecab353e77be6f",
    "libandroidx.graphics.path.map": "bc338abd36eeb27059572903ad167cf4231a36ca92be4eae3574501aa83f0d8c",
    "math/TVecHelpers.h": "1b0d6b06c5bbd6b438f9d8440ac78cf93fb8a713761badc59a4412b6457c1014",
    "math/compiler.h": "d53e85383580e5dbf81cbcb24426b0fe1bf419b4837540242dbdca3f1df4cf66",
    "math/vec2.h": "09e1a8eb3f8fdf9c1071500f1a4933f67caeb6d0f765d5c44ba968370de9fcb1",
    "pathway.cpp": "4be68d6fdb6376e95560f7c49a79aa0cd97218d758cf11ea3230ac9124485800",
    "scalar.h": "b1d2bba80a4c9272d84473b6f09f700972b016f7579842d3a87bdbbdb2af1edc",
}
SOURCE_MANIFEST_SHA256 = hashlib.sha256("".join(
    f"{sha}  {name}\n" for name, sha in sorted(SOURCE_FILES.items())).encode()).hexdigest()
BASELINE_URL = ("https://dl.google.com/dl/android/maven2/androidx/graphics/graphics-path/"
                "1.0.1/graphics-path-1.0.1.aar")
BASELINE_SHA256 = "8ca4032b6d79b351f0b59ad4b580eddbb9423e1652f7c958830687f1eee2ec03"
LIBRARY = "libandroidx.graphics.path.so"
AAR = "graphics-path-1.0.1-quasar.aar"

def check_source(source: Path) -> None:
    # Gitiles archive mtimes vary; pin every file's contents instead of archive headers.
    with tarfile.open(source) as archive:
        actual = {}
        for entry in archive.getmembers():
            if entry.isdir():
                continue
            if not entry.isfile() or entry.name in actual:
                raise ValueError("Unexpected graphics source archive entry.")
            actual[entry.name] = hashlib.sha256(archive.extractfile(entry).read()).hexdigest()
        if actual != SOURCE_FILES:
            raise ValueError("Official graphics source file hashes do not match the release revision.")


def build(ndk: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    source, baseline = out / "native-source.tar.gz", out / "baseline.aar"
    urllib.request.urlretrieve(SOURCE_URL, source)
    check_source(source)
    fetch(BASELINE_URL, baseline, BASELINE_SHA256)
    work = out / "source"
    work.mkdir()
    with tarfile.open(source) as archive:
        archive.extractall(work, filter="data")
    toolchain = ndk / "toolchains" / "llvm" / "prebuilt" / "linux-x86_64" / "bin"
    flags = ["-shared", "-O2", "-DNDEBUG", "-std=c++17", "-fPIC", "-fno-exceptions", "-fno-rtti",
             "-fno-unwind-tables", "-fno-asynchronous-unwind-tables", "-ffast-math",
             "-ffp-contract=fast", "-fvisibility-inlines-hidden", "-fvisibility=hidden",
             "-fomit-frame-pointer", "-ffunction-sections", "-fdata-sections", "-nostdlib++",
             "-Wl,--hash-style=both,--gc-sections,-Bsymbolic-functions,--no-undefined",
             "-Wl,-z,max-page-size=16384,-z,common-page-size=16384,-z,relro,-z,now",
             f"-Wl,--version-script={work / 'libandroidx.graphics.path.map'}"]
    report = {"sourceUrl": SOURCE_URL, "sourceManifestSHA256": SOURCE_MANIFEST_SHA256,
              "sourceFilesSHA256": SOURCE_FILES, "sourceArchiveSHA256": digest(source),
              "sourceCommit": COMMIT,
              "baselineAarSHA256": BASELINE_SHA256, "ndk": "28.2.13676358", "api": 26,
              "flags": flags, "androidRuntimeTested": False, "libraries": []}
    with zipfile.ZipFile(baseline) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()
                   if not name.endswith("/") and not name.startswith("jni/")}
        for abi, (_, compiler) in ABIS.items():
            library = out / "jni" / abi / LIBRARY
            library.parent.mkdir(parents=True)
            run([str(toolchain / f"{compiler}26-clang++"), *flags,
                 "Conic.cpp", "PathIterator.cpp", "pathway.cpp", "-o", str(library)], work)
            subprocess.run([str(toolchain / "llvm-strip"), "--strip-unneeded", str(library)], check=True)
            old = out / f"baseline-{abi}.so"
            old.write_bytes(archive.read(f"jni/{abi}/{LIBRARY}"))
            previous = exports(toolchain / "llvm-nm", old)
            current = exports(toolchain / "llvm-nm", library)
            if previous != current:
                raise ValueError(f"Native JNI export API changed: {abi}")
            segments = elf_segments(library.read_bytes())
            loads = [s for s in segments if s["type"] == "LOAD"]
            relro = [s for s in segments if s["type"] == "GNU_RELRO"]
            if not loads or not all(s["align"] >= 16384 and
                    (s["vaddr"] - s["offset"]) % 16384 == 0 for s in loads):
                raise ValueError(f"Invalid LOAD alignment: {abi}")
            if not relro or not all((s["vaddr"] + s["memSize"]) % 16384 == 0 for s in relro):
                raise ValueError(f"Invalid RELRO boundary: {abi}")
            entries[f"jni/{abi}/{LIBRARY}"] = library.read_bytes()
            report["libraries"].append({"abi": abi, "sha256": digest(library),
                                        "segments": segments, "exports": sorted(current)})
    with zipfile.ZipFile(out / AAR, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data, compresslevel=9)
    report["aarSHA256"] = digest(out / AAR)
    (out / "graphics-provenance.json").write_text(json.dumps(report, indent=2) + "\n")


def verify(out: Path) -> None:
    report = json.loads((out / "graphics-provenance.json").read_text())
    if (report["sourceManifestSHA256"] != SOURCE_MANIFEST_SHA256 or report["sourceCommit"] != COMMIT
            or report["sourceFilesSHA256"] != SOURCE_FILES
            or report["baselineAarSHA256"] != BASELINE_SHA256 or report["ndk"] != "28.2.13676358"
            or report["aarSHA256"] != digest(out / AAR)):
        raise ValueError("Graphics native artifact provenance/hash mismatch.")
    baseline = out / "verification-baseline.aar"
    fetch(BASELINE_URL, baseline, BASELINE_SHA256)
    with zipfile.ZipFile(out / AAR) as archive, zipfile.ZipFile(baseline) as original:
        if set(archive.namelist()) != {n for n in original.namelist() if not n.endswith("/")}:
            raise ValueError("Graphics binding archive members changed.")
        for name in archive.namelist():
            data = archive.read(name)
            if not name.startswith("jni/") and data != original.read(name):
                raise ValueError(f"Graphics Java binding/resources changed: {name}")
        if {lib["abi"] for lib in report["libraries"]} != set(ABIS):
            raise ValueError("Graphics artifact requires all four ABIs.")
        for lib in report["libraries"]:
            data = archive.read(f"jni/{lib['abi']}/{LIBRARY}")
            if hashlib.sha256(data).hexdigest() != lib["sha256"]:
                raise ValueError("Graphics native library hash mismatch.")
            segments = elf_segments(data)
            if not all(s["align"] >= 16384 and (s["vaddr"] - s["offset"]) % 16384 == 0
                       for s in segments if s["type"] == "LOAD"):
                raise ValueError("Graphics LOAD alignment mismatch.")
            if not all((s["vaddr"] + s["memSize"]) % 16384 == 0
                       for s in segments if s["type"] == "GNU_RELRO"):
                raise ValueError("Graphics RELRO boundary mismatch.")
    baseline.unlink()
    print("Graphics AAR verified: original binding/resources unchanged; all four native ABIs aligned.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ndk", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        verify(args.out)
    else:
        if args.ndk is None:
            parser.error("--ndk is required when building")
        build(args.ndk.resolve(), args.out.resolve())
        verify(args.out.resolve())
