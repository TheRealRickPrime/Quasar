"""Read every finalized ZIP and verify its payload, manifest and signed-APK evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlparse

from release import Edition, REPO, __version__, assert_public, sha256
from quasar_win.updater import parse_manifest


def verify(out: Path) -> dict:
    artifacts = json.loads((out / "artifacts.json").read_text())
    manifest = json.loads((out / "latest.json").read_text())
    apks = {r["edition"]: r for r in json.loads((out / "apk-verification.json").read_text())}
    expected = {(platform, e.value) for platform in ("windows", "android") for e in Edition}
    if len(artifacts) != 8 or {(a["platform"], a["edition"]) for a in artifacts} != expected:
        raise ValueError("Exactly eight platform/edition artifacts are required.")
    if set(apks) != {e.value for e in Edition}:
        raise ValueError("Four APK verification reports are required.")
    native = json.loads((REPO / "android" / "native" / "provenance.json").read_text())
    graphics = json.loads((REPO / "android" / "native" / "graphics-provenance.json").read_text())
    for report in apks.values():
        if not (report["sameSignerAs032"] and report["native16KBStaticCompatible"]
                and report["zipalign16KB"] and not report["runtimeDeviceTested"]):
            raise ValueError("APK verification gate has not passed.")
        for metadata, filename in ((native, "libsodium.so"), (graphics, "libandroidx.graphics.path.so")):
            for library in metadata["libraries"]:
                matching = [lib for lib in report["nativeLibraries"]
                            if lib["file"] == f"lib/{library['abi']}/{filename}"]
                if len(matching) != 1 or matching[0]["sha256"] != library["sha256"]:
                    raise ValueError(f"Packaged {filename} differs from its verified native build.")
    expected_sums = "".join(f"{a['sha256']}  {a['file']}\n" for a in artifacts)
    if (out / "SHA256SUMS.txt").read_text() != expected_sums:
        raise ValueError("Outer SHA256SUMS differs from artifacts metadata.")
    if {p.name for p in out.glob("*.zip")} != {a["file"] for a in artifacts}:
        raise ValueError("Unexpected or missing staged ZIP.")
    checked = []
    for artifact in artifacts:
        path = out / artifact["file"]
        if sha256(path) != artifact["sha256"] or path.stat().st_size != artifact["bytes"]:
            raise ValueError(f"Final ZIP hash/size mismatch: {path.name}")
        platform, edition = artifact["platform"], Edition(artifact["edition"])
        entry = manifest[platform]["editions"][edition.value]
        if unquote(urlparse(entry["url"]).path.split("/")[-1]) != path.name:
            raise ValueError("Update URL does not point to its finalized artifact.")
        if entry["sha256"] != artifact["sha256"] or entry["version"] != __version__:
            raise ValueError("Update entry differs from finalized artifact.")
        if platform == "windows" and parse_manifest(manifest, "0.0.0", edition) != entry:
            raise ValueError("Windows updater did not select the exact edition.")
        android = manifest["android"]["editions"][edition.value]
        prefix = "Quasar/" if platform == "windows" else ""
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)) or archive.testzip() is not None:
                raise ValueError("Duplicate/corrupt ZIP members.")
            expected_payload = {}
            for line in archive.read("SHA256SUMS.txt").decode().splitlines():
                digest, name = line.split("  ", 1)
                expected_payload[name] = digest
            if set(expected_payload) != set(names) - {"SHA256SUMS.txt"}:
                raise ValueError("Internal payload manifest does not cover every member.")
            for name, digest in expected_payload.items():
                assert_public(Path(name))
                actual = hashlib.sha256()
                with archive.open(name) as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        actual.update(block)
                if actual.hexdigest() != digest:
                    raise ValueError(f"Payload hash mismatch: {name}")
            apk_names = [name for name in names if name.endswith(".apk")]
            if len(apk_names) != 1 or apk_names[0].split("/")[-1] != android["apkFile"]:
                raise ValueError("ZIP does not contain exactly its matching APK.")
            apk_hash = expected_payload[apk_names[0]]
            if apk_hash != android["apkSha256"] or apk_hash != apks[edition.value]["sha256"]:
                raise ValueError("Embedded APK differs from signature/static-verified bytes.")
            if platform == "windows":
                identity = json.loads(archive.read("Quasar/distribution.json"))
                if identity != {"edition": edition.value, "version": __version__}:
                    raise ValueError("Windows distribution identity mismatch.")
            if json.loads(archive.read(prefix + "NATIVE-PROVENANCE.json")) != native:
                raise ValueError("Missing or incorrect native provenance.")
            if json.loads(archive.read(prefix + "GRAPHICS-NATIVE-PROVENANCE.json")) != graphics:
                raise ValueError("Missing or incorrect graphics native provenance.")
        checked.append({"file": path.name, "sha256": artifact["sha256"],
                        "bytes": artifact["bytes"], "embeddedApkSHA256": apk_hash})
        print(f"Verified {path.name}")
    if manifest["android"]["version"] != "0.3.2" or manifest["android"]["versionCode"] != 5:
        raise ValueError("Legacy Android manifest identity was changed.")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    result = {"sourceCommit": commit, "version": __version__, "artifacts": checked,
              "allPayloadHashesVerified": True, "allApksSameOriginalSigner": True,
              "allApks16KBStaticVerified": True, "androidRuntimeDeviceTested": False,
              "sigstoreSigned": False, "published": False,
              "nativeBuildRun": native["ciRun"], "graphicsBuildRun": graphics["ciRun"]}
    (out / "release-verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=REPO / "release-staging" / __version__)
    verify(parser.parse_args().out)
