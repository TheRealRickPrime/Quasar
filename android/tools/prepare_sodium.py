"""Repackage the unchanged official Java binding with verified Quasar-CI native libraries."""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path

from build_sodium import BASELINE_SHA256, BASELINE_URL, SOURCE_SHA256
from verify_apk import elf_segments


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(artifact: Path, out: Path, run_url: str) -> None:
    report = json.loads((artifact / "build-report.json").read_text())
    if (report["sourceSHA256"] != SOURCE_SHA256 or report["ndk"] != "28.2.13676358"
            or report["baselineAarSHA256"] != BASELINE_SHA256):
        raise ValueError("Native artifact provenance does not match the pinned build.")
    required = {"arm64-v8a", "armeabi-v7a", "x86_64", "x86"}
    if {lib["abi"] for lib in report["libraries"]} != required:
        raise ValueError("Native artifact does not contain all required ABIs.")
    entries = {}
    for library in report["libraries"]:
        abi = library["abi"]
        path = artifact / "jni" / abi / "libsodium.so"
        if sha(path) != library["sha256"] or library["missingExports"]:
            raise ValueError(f"Native hash/export mismatch: {abi}")
        segments = elf_segments(path.read_bytes())
        if not all(s["align"] >= 16384 and (s["vaddr"] - s["offset"]) % 16384 == 0
                   for s in segments if s["type"] == "LOAD"):
            raise ValueError(f"Invalid LOAD alignment: {abi}")
        relro = [s for s in segments if s["type"] == "GNU_RELRO"]
        if not relro or not all((s["vaddr"] + s["memSize"]) % 16384 == 0 for s in relro):
            raise ValueError(f"Invalid RELRO boundary: {abi}")
        entries[f"jni/{abi}/libsodium.so"] = path.read_bytes()
    tests = list((artifact / "kotlin-test-results").glob("TEST-*.xml"))
    if not tests or not any('tests="1"' in path.read_text() and 'failures="0"' in path.read_text()
                            and 'skipped="0"' in path.read_text() for path in tests):
        raise ValueError("A successful, non-skipped Kotlin crypto-format test is required.")
    out.mkdir(parents=True, exist_ok=True)
    baseline = out / "baseline.aar"
    urllib.request.urlretrieve(BASELINE_URL, baseline)
    if sha(baseline) != BASELINE_SHA256:
        raise ValueError("Official Java binding SHA256 mismatch.")
    with zipfile.ZipFile(baseline) as archive:
        for name in archive.namelist():
            if not name.endswith("/") and not name.startswith("jni/"):
                entries[name] = archive.read(name)
    license_text = (artifact / "LICENSE").read_text()
    entries["assets/quasar-libsodium-LICENSE.txt"] = license_text.encode()
    target = out / "lazysodium-android-5.1.0-quasar.aar"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(entries.items()):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content, compresslevel=9)
    baseline.unlink()
    report.update(ciRun=run_url, aarSHA256=sha(target),
                  javaBinding="Unchanged classes.jar from official lazysodium-android 5.1.0")
    (out / "provenance.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (out / "LICENSE.libsodium").write_text(license_text, encoding="utf-8")
    evidence = out / "kotlin-test-results"
    evidence.mkdir(exist_ok=True)
    for test in tests:
        (evidence / test.name).write_bytes(test.read_bytes())
    print(f"{sha(target)}  {target}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "native")
    parser.add_argument("--run-url", required=True)
    args = parser.parse_args()
    prepare(args.artifact, args.out, args.run_url)
