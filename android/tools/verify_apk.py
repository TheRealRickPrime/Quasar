"""Static APK signature, identity, ABI and 16 KB checks. Does not install or run anything."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
import zipfile
from pathlib import Path


def command(*args: str | Path) -> str:
    result = subprocess.run([str(arg) for arg in args], capture_output=True, text=True, check=True)
    return result.stdout + result.stderr


def certificate(apk: Path, build_tools: Path) -> str:
    output = command(build_tools / "apksigner.bat", "verify", "--verbose", "--print-certs", apk)
    match = re.search(r"Signer #1 certificate SHA-256 digest: ([0-9a-fA-F]+)", output)
    if not match:
        raise ValueError("No APK signer certificate found")
    return match.group(1).lower()


def elf_segments(data: bytes) -> list[dict]:
    if data[:4] != b"\x7fELF" or data[5] != 1:
        raise ValueError("Expected little-endian ELF")
    is64 = data[4] == 2
    if is64:
        offset = struct.unpack_from("<Q", data, 32)[0]
        size, count = struct.unpack_from("<HH", data, 54)
    else:
        offset = struct.unpack_from("<I", data, 28)[0]
        size, count = struct.unpack_from("<HH", data, 42)
    segments = []
    for i in range(count):
        values = struct.unpack_from("<IIQQQQQQ" if is64 else "<IIIIIIII", data, offset + i * size)
        if is64:
            kind, _, file_offset, vaddr, _, _, mem_size, align = values
        else:
            kind, file_offset, vaddr, _, _, mem_size, _, align = values
        if kind in (1, 0x6474E552):
            segments.append({"type": "LOAD" if kind == 1 else "GNU_RELRO",
                             "offset": file_offset, "vaddr": vaddr, "memSize": mem_size, "align": align})
    return segments


def inspect(apk: Path, sdk: Path, legacy: Path) -> dict:
    tools = sdk / "build-tools" / "35.0.0"
    signer = certificate(apk, tools)
    if signer != certificate(legacy, tools):
        raise ValueError("Release signer differs from the existing 0.3.2 APK")
    badging = command(tools / "aapt.exe", "dump", "badging", apk)
    package = re.search(r"package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'", badging)
    minimum = re.search(r"sdkVersion:'(\d+)'", badging)
    target = re.search(r"targetSdkVersion:'(\d+)'", badging)
    if not package or package.groups() != ("com.quasar.mobile", "6", "0.4.0"):
        raise ValueError("Unexpected APK package/version")
    if not minimum or not target or (minimum.group(1), target.group(1)) != ("26", "35"):
        raise ValueError("Unexpected minimum/target SDK")
    alignment = command(tools / "zipalign.exe", "-v", "-c", "-P", "16", "4", apk)
    libraries = []
    with zipfile.ZipFile(apk) as archive:
        for entry in archive.infolist():
            if entry.filename.startswith("lib/") and entry.filename.endswith(".so"):
                segments = elf_segments(archive.read(entry))
                abi = entry.filename.split("/")[1]
                relevant = abi in ("arm64-v8a", "x86_64")
                loads = [s for s in segments if s["type"] == "LOAD"]
                relro = [s for s in segments if s["type"] == "GNU_RELRO"]
                libraries.append({
                    "file": entry.filename, "abi": abi, "segments": segments,
                    "sha256": hashlib.sha256(archive.read(entry)).hexdigest(),
                    "load16KB": bool(loads) and all(s["align"] >= 16384 and
                        (s["vaddr"] - s["offset"]) % 16384 == 0 for s in loads),
                    "relroPresent": bool(relro),
                    "relro16KB": all((s["vaddr"] + s["memSize"]) % 16384 == 0 for s in relro),
                    "pageSizeRelevant": relevant,
                })
    by_abi = {}
    for library in libraries:
        by_abi.setdefault(library["abi"], []).append(Path(library["file"]).name)
    for abi in ("arm64-v8a", "armeabi-v7a", "x86_64", "x86"):
        names = by_abi.get(abi, [])
        for required in ("zstd", "sodium", "jnidispatch"):
            if not any(required in name for name in names):
                raise ValueError(f"Missing {required} native dependency for {abi}")
    compatible = all(lib["load16KB"] and lib["relro16KB"] for lib in libraries if lib["pageSizeRelevant"])
    return {
        "file": str(apk), "sha256": hashlib.sha256(apk.read_bytes()).hexdigest(),
        "applicationId": package.group(1), "versionCode": int(package.group(2)),
        "version": package.group(3), "minSdk": int(minimum.group(1)), "targetSdk": int(target.group(1)),
        "signerSHA256": signer, "sameSignerAs032": True, "abis": by_abi,
        "zipalign16KB": "Verification successful" in alignment,
        "native16KBStaticCompatible": compatible, "nativeLibraries": libraries,
        "runtimeDeviceTested": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apks", type=Path, nargs="+")
    parser.add_argument("--sdk", type=Path, default=Path(r"D:\Tools\android-sdk"))
    parser.add_argument("--legacy", type=Path, default=Path(__file__).resolve().parents[2] /
                        "windows" / "assets" / "apk" / "Quasar-Android-0.3.2.apk")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    reports = [inspect(apk, args.sdk, args.legacy) for apk in args.apks]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    for report in reports:
        print(f"{report['file']}: signer={report['signerSHA256']} ABIs={','.join(report['abis'])} "
              f"16KB_ELF={report['native16KBStaticCompatible']} zipalign={report['zipalign16KB']}")
    if not all(r["native16KBStaticCompatible"] and r["zipalign16KB"] for r in reports):
        raise SystemExit("Release blocked: a native ELF or APK 16 KB alignment check failed.")
