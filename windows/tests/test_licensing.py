import base64
import json
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from quasar_win import licensing as lic

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import make_license  # noqa: E402


@pytest.fixture()
def keys(tmp_path):
    key = Ed25519PrivateKey.generate()
    priv = tmp_path / "private.key"
    priv.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                       serialization.NoEncryption()))
    pub = base64.b64encode(key.public_key().public_bytes(serialization.Encoding.Raw,
                                                         serialization.PublicFormat.Raw)).decode()
    return priv, pub


def test_key_roundtrip_and_tamper(keys):
    priv, pub = keys
    key = make_license.make_key("pro", "a@b.c", private_key=priv)
    assert lic.verify_key(key, pub).tier == "pro"
    head, payload, sig = key.split(".")
    forged = json.loads(lic._b64d(payload))
    forged["tier"] = "supporter"
    bad = base64.urlsafe_b64encode(json.dumps(forged, separators=(",", ":")).encode()).rstrip(b"=").decode()
    for broken in (f"{head}.{bad}.{sig}", "garbage", key[:-4] + "AAAA"):
        with pytest.raises(lic.LicenseError):
            lic.verify_key(broken, pub)
    other = Ed25519PrivateKey.generate().public_key().public_bytes(serialization.Encoding.Raw,
                                                                   serialization.PublicFormat.Raw)
    with pytest.raises(lic.LicenseError):
        lic.verify_key(key, base64.b64encode(other).decode())


def test_expired_key_rejected(keys):
    priv, pub = keys
    with pytest.raises(lic.LicenseError, match="expired"):
        lic.verify_key(make_license.make_key("pro", "a@b.c", "2020-01-01", priv), pub)


def test_embedded_public_key_matches_seller_key():
    real = Path(make_license.DEFAULT_KEY)
    if not real.exists():
        pytest.skip("seller private key not on this machine")
    assert lic.verify_key(make_license.make_key("supporter", "t@t.t", private_key=real)).tier == "supporter"


def test_free_limits_and_upgrade(tmp_path, keys):
    priv, pub = keys
    lc = lic.Licensing(tmp_path, pub)
    assert lc.tier.key == "free"
    for _ in range(15):
        assert lc.check_backup() == ""
        lc.record_backup()
    assert "15 backups" in lc.check_backup()

    assert lc.check_upload(1 * lic.GB) == ""
    lc.record_upload(int(1.5 * lic.GB))
    assert "2 GB" in lc.check_upload(1 * lic.GB)

    lc.activate(make_license.make_key("supporter", "a@b.c", private_key=priv))
    assert lc.tier.key == "supporter" and lc.check_backup() == ""
    assert lc.check_upload(10 * lic.GB) == "" and "50 GB" in lc.check_upload(60 * lic.GB)

    lc.activate(make_license.make_key("pro", "a@b.c", private_key=priv))
    assert lc.check_upload(10_000 * lic.GB) == ""
    lc.deactivate()
    assert lc.tier.key == "free"


def test_usage_resets_each_month(tmp_path):
    lc = lic.Licensing(tmp_path)
    (tmp_path / "usage.json").write_text(json.dumps({"month": "1999-01", "backups": 99, "upload_bytes": 99}))
    assert lc.backups_used == 0 and lc.upload_used == 0


def test_license_next_to_exe_is_picked_up(tmp_path, keys, monkeypatch):
    priv, pub = keys
    exe_dir = tmp_path / "exe"
    exe_dir.mkdir()
    (exe_dir / "license.key").write_text(make_license.make_key("pro", "z@z.z", private_key=priv))
    monkeypatch.setattr(lic, "_exe_dir", lambda: exe_dir)
    assert lic.Licensing(tmp_path / "data_missing_ok" if False else tmp_path, pub).tier.key == "pro"


class _Resp:
    def __init__(self, data):
        self._d = data

    def json(self):
        return self._d


def test_gumroad_activation_and_refund(tmp_path, monkeypatch):
    import requests

    def post(url, data=None, timeout=0):
        if data["license_key"] == "GOOD" and data["product_permalink"] == "qwjtj":
            return _Resp({"success": True, "purchase": {"email": "b@x.y", "id": "abcdefghij"}})
        if data["license_key"] == "REFUND" and data["product_permalink"] == "qygwf":
            return _Resp({"success": True, "purchase": {"refunded": True}})
        return _Resp({"success": False})

    monkeypatch.setattr(requests, "post", post)
    lc = lic.Licensing(tmp_path)
    assert lc.activate("GOOD").tier == "pro" and lc.tier.key == "pro"
    assert lic.Licensing(tmp_path).tier.key == "pro"  # served from cache
    with pytest.raises(lic.LicenseError, match="refunded"):
        lc.activate("REFUND")
    with pytest.raises(lic.LicenseError, match="wasn't found"):
        lc.activate("NOPE")
    lc.deactivate()
    assert lc.tier.key == "free"


def test_gumroad_offline_error(tmp_path, monkeypatch):
    import requests

    def post(*a, **k):
        raise requests.ConnectionError()

    monkeypatch.setattr(requests, "post", post)
    with pytest.raises(lic.LicenseError, match="Couldn't reach"):
        lic.Licensing(tmp_path).activate("ANY")

