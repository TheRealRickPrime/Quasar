import hashlib
import json
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import release  # noqa: E402
from quasar_win.editions import Edition  # noqa: E402


def test_eight_public_archives_match_their_edition_and_manifest(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "Quasar.exe").write_bytes(b"synthetic exe")
    assets = dist / "_internal" / "assets" / "apk"
    assets.mkdir(parents=True)
    (assets / "old.apk").write_bytes(b"old")
    apk_root = tmp_path / "apk"
    for edition in Edition:
        flavor = release.FLAVORS[edition.value]
        path = apk_root / flavor / "release" / f"app-{flavor}-release.apk"
        path.parent.mkdir(parents=True)
        path.write_bytes(f"synthetic {edition.value}".encode())
    out = tmp_path / "out"
    manifest = release.package(dist, apk_root, out)
    assert len(list(out.glob("*.zip"))) == 8
    for edition in Edition:
        for platform in ("windows", "android"):
            entry = manifest[platform]["editions"][edition.value]
            path = out / entry["url"].split("/")[-1]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                assert not any(name.lower().endswith("license.key") for name in names)
                assert sum(name.endswith(".apk") for name in names) == 1
                assert not any("old.apk" in name for name in names)
                assert "SHA256SUMS.txt" in names
                prefix = "Quasar/" if platform == "windows" else ""
                assert prefix + "NATIVE-PROVENANCE.json" in names
                assert prefix + "LICENSE.lazysodium" in names
                assert len(json.loads(archive.read(prefix + "NATIVE-PROVENANCE.json"))["sourceSHA256"]) == 64
                assert b"Mozilla" in archive.read(prefix + "LICENSE.lazysodium")
                if platform == "windows":
                    assert json.loads(archive.read("Quasar/distribution.json"))["edition"] == edition.value
                else:
                    assert hashlib.sha256(archive.read(entry["apkFile"])).hexdigest() == entry["apkSha256"]
    assert manifest["android"]["version"] == "0.3.2" and manifest["android"]["versionCode"] == 5
    assert "OWNER" not in (out / "SHA256SUMS.txt").read_text()
    with pytest.raises(FileExistsError):
        release.package(dist, apk_root, out)


@pytest.mark.parametrize("name", ["license.key", "nested/private.key", "android-signing.properties", "OWNER.zip"])
def test_rejects_private_material(name):
    with pytest.raises(ValueError):
        release.assert_public(Path(name))


def test_public_ca_bundle_is_not_a_private_signing_key():
    release.assert_public(Path("_internal/certifi/cacert.pem"))
