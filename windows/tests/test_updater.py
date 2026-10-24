import hashlib
from unittest import mock

import pytest

from quasar_win import updater
from quasar_win.editions import Edition


def _resp(data):
    m = mock.Mock()
    m.json.return_value = data
    m.raise_for_status.return_value = None
    return m


MANIFEST = {"version": "0.4.0", "windows": {"url": "https://example.invalid/q.zip", "sha256": "a" * 64}}


def test_newer_version_detected():
    with mock.patch("requests.get", return_value=_resp(MANIFEST)):
        assert updater.check("0.3.0")["version"] == "0.4.0"


def test_same_or_older_means_no_update():
    with mock.patch("requests.get", return_value=_resp(MANIFEST)):
        assert updater.check("0.4.0") is None
        assert updater.check("0.10.0") is None


def test_download_rejects_bad_hash():
    resp = mock.MagicMock()
    resp.__enter__.return_value = resp
    resp.headers = {}
    resp.iter_content.return_value = [b"data"]
    entry = {"url": "http://x", "sha256": "0" * 64}
    with mock.patch("requests.get", return_value=resp), pytest.raises(updater.UpdateError):
        updater.download(entry)
    entry["sha256"] = hashlib.sha256(b"data").hexdigest()
    with mock.patch("requests.get", return_value=resp):
        assert updater.download(entry).read_bytes() == b"data"


def test_editions_and_platform_versions():
    data = {"schemaVersion": 2, "version": "9.0.0", "windows": {
        "version": "0.4.0", "editions": {
            e.value: {"version": "0.4.0", "url": f"https://example.invalid/{e.value}.zip", "sha256": "b" * 64}
            for e in Edition}}}
    for edition in Edition:
        entry = updater.parse_manifest(data, "0.3.3", edition)
        assert entry["url"].endswith(f"/{edition.value}.zip")
        assert entry["version"] == "0.4.0"
        assert updater.parse_manifest(data, "0.4.0", edition) is None
    del data["windows"]["editions"]["pro"]
    with pytest.raises(updater.UpdateError):
        updater.parse_manifest(data, "0.3.3", Edition.PRO)
    with pytest.raises(updater.UpdateError):
        updater.parse_manifest(MANIFEST, "0.3.3", Edition.FREE_ADS)


@pytest.mark.parametrize("name", ["../Quasar.exe", "Quasar/license.key", "C:/Quasar.exe"])
def test_stage_rejects_unsafe_or_personal_files(tmp_path, name):
    import zipfile
    path = tmp_path / "update.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(name, b"not executable")
    with pytest.raises(updater.UpdateError):
        updater.stage(path)
