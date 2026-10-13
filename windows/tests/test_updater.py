import hashlib
from unittest import mock

import pytest

from quasar_win import updater


def _resp(data):
    m = mock.Mock()
    m.json.return_value = data
    m.raise_for_status.return_value = None
    return m


MANIFEST = {"version": "0.4.0", "windows": {"url": "http://x/q.zip", "sha256": "ab"}}


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
