"""Package eight public distributions. Never generates or includes owner/buyer licenses."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))
from quasar_win import __version__  # noqa: E402
from quasar_win.editions import Edition  # noqa: E402
from quasar_win.privacy import DELETE_NOTICE, LEGAL_NOTICE  # noqa: E402

ASSET_BASE = "https://github.com/QuasarLI/QuasarLI.github.io/releases/download"
FLAVORS = {"free": "free", "free-ads": "freeAds", "supporter": "supporter", "pro": "pro"}
FORBIDDEN = {
    "license.key", "private.key", "gumroad.json", "usage.json", "settings.json", "history.json",
    "android-signing.properties", "quasar-release.jks", "license-imported",
}
VERIFY = """Verify the exact ZIP before extracting using its published Sigstore bundle.
Expected certificate identity:
https://github.com/QuasarLI/QuasarLI.github.io/.github/workflows/release-quasar.yml@refs/heads/main
Expected OIDC issuer: https://token.actions.githubusercontent.com
Example (with the Sigstore Python CLI installed):
python -m sigstore verify identity --bundle <ZIP>.sigstore.json --cert-identity https://github.com/QuasarLI/QuasarLI.github.io/.github/workflows/release-quasar.yml@refs/heads/main --cert-oidc-issuer https://token.actions.githubusercontent.com <ZIP>
SHA256 detects changed bytes; compare against the published verified SHA256SUMS.txt.
Sigstore is not Windows Authenticode and does not replace Android APK signing.
This package's creation alone does not mean it has been Sigstore signed or published.
"""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def assert_public(path: Path) -> None:
    for part in path.parts:
        name = part.lower()
        if (name in FORBIDDEN or name.endswith((".jks", ".keystore", ".p12", ".pfx"))
                or (name.endswith(".pem") and name != "cacert.pem")
                or "owner" in name):
            raise ValueError(f"Private or personal material must not be packaged: {path.name}")


def readme(platform: str, edition: Edition, apk_name: str) -> str:
    limits = "10 backups/month, 2 GB upload/month" if edition is Edition.FREE_ADS else "6 backups/month, 2 GB upload/month"
    instructions = (
        "Run Quasar\\Quasar.exe; keep the entire folder together. No installer is needed.\n"
        "The Android App page contains the matching signed APK; installation needs your explicit action.\n"
        "Update the existing folder while Quasar is closed, or use License > Check for updates.\n"
        "Settings, usage and activation remain under %APPDATA%\\Quasar, shared by all editions.\n"
    ) if platform == "Windows" else (
        f"Open {apk_name} with Android's package installer and explicitly approve installation.\n"
        "Package: com.quasar.mobile. Requires Android 8.0/API 26 or later.\n"
        "All editions share the same application ID and release signer. Install as an update; do not\n"
        "uninstall or clear storage when changing editions if you wish to keep activation and usage.\n"
        "Direct cloud upload is not implemented on Android; save with the system document picker.\n"
    )
    return (
        f"Quasar {platform} {__version__} - {edition.label}\n\n" + instructions +
        f"\nUnactivated package: {limits}. Supporter/Pro packages fall back to Free, not paid access.\n"
        "Free without ads is available. Free with Ads has optional affiliate recommendations only on\n"
        "Privacy & data; no automatic downloads, ad SDKs or tracking requests. Valid paid users see no ads.\n"
        "Supporter: $10, 15 backups and 30 GB upload/month. Pro: $25 one-time, unlimited backups/upload.\n"
        "Upload allowances are not hosted storage. Your provider's charges/capacity/terms still apply.\n"
        "Paid activation: License page > enter the key from your Gumroad receipt > Activate.\n"
        "Supporter purchase: https://quasarlabs3.gumroad.com/l/qygwf\n"
        "Pro purchase: https://quasarlabs3.gumroad.com/l/qwjtj\n"
        "No buyer/owner key is included. Gumroad needs internet for activation and periodic rechecks;\n"
        "3-day recheck interval, up to 30-day offline grace after a successful check. Refunds/disputes\n"
        "invalidate entitlement. Edition changes and license removal do not reset monthly counters.\n\n"
        "Android compatibility: 16 KB ELF LOAD/RELRO and APK ZIP alignment are statically checked.\n"
        "Official libsodium was rebuilt from pinned source; the Java binding and QSR1 format remain.\n"
        "Zstd arm64 has no RELRO segment (a hardening caveat, not a misaligned boundary).\n"
        "Static checks/host crypto tests do not prove runtime/device compatibility. No emulator or\n"
        "physical-device testing is claimed. See NATIVE-PROVENANCE.json and third-party notices.\n\n"
        "Privacy & data in the app explains local settings, backups, provider copies and deletion.\n"
        + DELETE_NOTICE + "\n" + LEGAL_NOTICE + "\n\n" + VERIFY +
        "\nSupport: quasarlabs-inc@outlook.com\n"
    )


def write_zip(target: Path, files: dict[str, Path], texts: dict[str, str]) -> None:
    if target.exists():
        raise FileExistsError(f"Refusing to replace a previously staged ZIP: {target}")
    hashes = []
    for name, path in files.items():
        assert_public(Path(name))
        hashes.append(f"{sha256(path)}  {name}")
    for name, text in texts.items():
        assert_public(Path(name))
        hashes.append(f"{hashlib.sha256(text.encode('utf-8')).hexdigest()}  {name}")
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, path in sorted(files.items()):
            archive.write(path, name)
        for name, text in sorted(texts.items()):
            archive.writestr(name, text)
        archive.writestr("SHA256SUMS.txt", "\n".join(sorted(hashes)) + "\n")


def package(dist: Path, apk_root: Path, out: Path, version_code: int = 6) -> dict:
    if not (dist / "Quasar.exe").is_file():
        raise FileNotFoundError("Build dist\\Quasar\\Quasar.exe first.")
    apks = {
        edition: apk_root / FLAVORS[edition.value] / "release" / f"app-{FLAVORS[edition.value]}-release.apk"
        for edition in Edition
    }
    for path in apks.values():
        if not path.is_file():
            raise FileNotFoundError(f"Missing release APK: {path}")
    base_files = {}
    for path in dist.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(dist)
        assert_public(relative)
        if path.suffix.lower() == ".apk" or relative.as_posix() == "distribution.json":
            continue
        base_files[str(PurePosixPath("Quasar", *relative.parts))] = path
    out.mkdir(parents=True, exist_ok=True)
    base = f"{ASSET_BASE}/v{__version__}"
    manifests = {"windows": {}, "android": {}}
    artifacts = []
    for edition, apk in apks.items():
        label = edition.artifact_label
        apk_name = f"Quasar-Android-{label}-{__version__}.apk"
        for platform in ("Windows", "Android"):
            filename = f"Quasar-{platform}-{label}-{__version__}.zip"
            target = out / filename
            if platform == "Windows":
                files = dict(base_files)
                asset_dir = "Quasar/_internal/assets/apk" if (dist / "_internal").is_dir() else "Quasar/assets/apk"
                files[f"{asset_dir}/{apk_name}"] = apk
                files["Quasar/LICENSE.txt"] = ROOT / "LICENSE.txt"
                texts = {
                    "Quasar/distribution.json": json.dumps({"edition": edition.value, "version": __version__}) + "\n",
                    "Quasar/README.txt": readme(platform, edition, apk_name),
                }
            else:
                files = {apk_name: apk, "LICENSE.txt": ROOT / "LICENSE.txt"}
                texts = {"README.txt": readme(platform, edition, apk_name)}
            notice_root = "Quasar/" if platform == "Windows" else ""
            native = REPO / "android" / "native"
            for source, name in (("provenance.json", "NATIVE-PROVENANCE.json"),
                                 ("LICENSE.libsodium", "LICENSE.libsodium"),
                                 ("LICENSE.lazysodium", "LICENSE.lazysodium"),
                                 ("LICENSE.zstd-jni", "LICENSE.zstd-jni"),
                                 ("LICENSE.zstd", "LICENSE.zstd"),
                                 ("LICENSE.Apache-2.0", "LICENSE.Apache-2.0")):
                files[f"{notice_root}{name}"] = native / source
            files[f"{notice_root}THIRD-PARTY-NOTICES.txt"] = native / "THIRD-PARTY-NOTICES.txt"
            write_zip(target, files, texts)
            entry = {"version": __version__, "url": f"{base}/{filename}", "sha256": sha256(target)}
            if platform == "Android":
                entry.update(versionCode=version_code, apkFile=apk_name, apkSha256=sha256(apk))
            manifests[platform.lower()][edition.value] = entry
            artifacts.append({"file": filename, "platform": platform.lower(), "edition": edition.value,
                              "bytes": target.stat().st_size, **entry})
            print(f"{entry['sha256']}  {filename}")
    legacy_apk = {
        "version": "0.3.2", "versionCode": 5,
        "url": f"{ASSET_BASE}/v0.3.3/Quasar-Android-0.3.2.apk",
        "sha256": "6940b502a6d5449416dfce5d6db452a60ea58a1a39aca8c2828c5e9d5eaf0994",
    }
    manifest = {
        "schemaVersion": 2, "version": __version__,
        "windows": {**manifests["windows"]["free"], "editions": manifests["windows"]},
        "android": {**legacy_apk, "editions": manifests["android"]},
    }
    (out / "latest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (out / "artifacts.json").write_text(json.dumps(artifacts, indent=2) + "\n", encoding="utf-8")
    (out / "SHA256SUMS.txt").write_text("".join(f"{a['sha256']}  {a['file']}\n" for a in artifacts), encoding="ascii")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=ROOT / "dist" / "Quasar")
    parser.add_argument("--apk-root", type=Path, default=REPO / "android" / "app" / "build" / "outputs" / "apk")
    parser.add_argument("--out", type=Path, default=REPO / "release-staging" / __version__)
    args = parser.parse_args()
    package(args.dist, args.apk_root, args.out)
