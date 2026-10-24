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


def test_embedded_public_key_is_ed25519():
    assert len(base64.b64decode(lic.PUBLIC_KEY_B64)) == 32


def test_free_limits_and_upgrade(tmp_path, keys):
    priv, pub = keys
    lc = lic.Licensing(tmp_path, pub)
    assert lc.tier.key == "free"
    for _ in range(6):
        assert lc.check_backup() == ""
        lc.record_backup()
    assert "6 backups" in lc.check_backup()

    assert lc.check_upload(1 * lic.GB) == ""
    lc.record_upload(int(1.5 * lic.GB))
    assert "2 GB" in lc.check_upload(1 * lic.GB)

    lc.activate(make_license.make_key("supporter", "a@b.c", private_key=priv))
    assert lc.tier.key == "supporter" and lc.check_backup() == ""
    assert lc.check_upload(10 * lic.GB) == "" and "30 GB" in lc.check_upload(60 * lic.GB)

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
    status_code = 200
    def __init__(self, data):
        self._d = data

    def json(self):
        return self._d


def test_gumroad_activation_and_refund(tmp_path, monkeypatch):
    import requests

    def post(url, data=None, timeout=0):
        if data["license_key"] == "GOOD" and data["product_id"] == "9R_AkG7S8By0ZotuYyM1Lg==":
            return _Resp({"success": True, "purchase": {"email": "b@x.y", "id": "abcdefghij", "short_product_id": "qwjtj"}})
        if data["license_key"] == "REFUND" and data["product_id"] == "7sQ_4QWbmr1Miy5LYzh-Bw==":
            return _Resp({"success": True, "purchase": {"refunded": True, "short_product_id": "qygwf"}})
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


def test_distribution_is_not_a_paid_entitlement_and_usage_carries(tmp_path, keys):
    from quasar_win.editions import Edition
    priv, pub = keys
    for edition in (Edition.SUPPORTER, Edition.PRO):
        assert lic.Licensing(tmp_path, pub, edition).tier.key == "free"
    free = lic.Licensing(tmp_path, pub, Edition.FREE)
    for _ in range(6):
        free.record_backup()
    free.record_upload(lic.GB)
    ads = lic.Licensing(tmp_path, pub, Edition.FREE_ADS)
    assert ads.tier.backups_per_month == 10
    assert ads.tier.upload_gb_per_month == 2 and ads.upload_used == lic.GB
    assert ads.show_affiliates and ads.backups_used == 6 and not ads.check_backup()
    for _ in range(4):
        ads.record_backup()
    assert "10 backups" in ads.check_backup()
    ads.activate(make_license.make_key("supporter", "synthetic@example.invalid", private_key=priv))
    assert not ads.show_affiliates and ads.backups_used == 10
    paid = lic.Licensing(tmp_path, pub, Edition.PRO)
    assert paid.tier.key == "supporter" and paid.backups_used == 10
    paid.deactivate()
    assert "6 backups" in paid.check_backup() and paid.upload_used == lic.GB


def test_imported_legacy_license_survives_update_but_not_deactivation(tmp_path, keys, monkeypatch):
    priv, pub = keys
    exe = tmp_path / "old-install"
    exe.mkdir()
    key = make_license.make_key("pro", "synthetic@example.invalid", private_key=priv)
    (exe / "license.key").write_text(key)
    monkeypatch.setattr(lic, "_exe_dir", lambda: exe)
    data = tmp_path / "appdata"
    manager = lic.Licensing(data, pub)
    assert (data / "license.key").read_text() == key
    (exe / "license.key").unlink()
    assert lic.Licensing(data, pub).tier.key == "pro"
    (exe / "license.key").write_text(key)
    manager.deactivate()
    assert lic.Licensing(data, pub).tier.key == "free"


def test_recheck_offline_expiry_refund_and_product_identity(tmp_path, monkeypatch):
    import requests
    now = [1_780_000_000.0]
    monkeypatch.setattr(lic.time, "time", lambda: now[0])
    response = {"success": True, "purchase": {"product_id": "7sQ_4QWbmr1Miy5LYzh-Bw=="}}
    def post(*args, **kwargs):
        if response is None:
            raise requests.ConnectionError()
        return _Resp(response)
    monkeypatch.setattr(requests, "post", post)
    manager = lic.Licensing(tmp_path)
    manager.activate("SYNTHETIC-TEST-ONLY")
    response = None
    now[0] += 10 * 86400
    assert lic.Licensing(tmp_path).tier.key == "supporter"
    now[0] += 21 * 86400
    assert manager.tier.key == "free"
    assert lic.Licensing(tmp_path).tier.key == "free"
    response = {"success": True, "purchase": {"short_product_id": "qygwf", "refunded": True}}
    assert lic.Licensing(tmp_path).tier.key == "free"
    response = None
    assert lic.Licensing(tmp_path).tier.key == "free"
    response = {"success": True, "purchase": {"product_id": "unrelated", "short_product_id": "qwjtj"}}
    with pytest.raises(lic.LicenseError, match="wasn't found"):
        manager.activate("SYNTHETIC-TEST-ONLY")


def test_rechecks_only_when_due_and_handles_invalid_cache(tmp_path, monkeypatch):
    import requests
    now = [1_780_000_000.0]
    monkeypatch.setattr(lic.time, "time", lambda: now[0])
    calls = []
    def post(*args, **kwargs):
        calls.append(kwargs["data"])
        return _Resp({"success": True, "purchase": {"product_id": "7sQ_4QWbmr1Miy5LYzh-Bw=="}})
    monkeypatch.setattr(requests, "post", post)
    manager = lic.Licensing(tmp_path)
    manager.activate("SYNTHETIC-TEST-ONLY")
    assert calls[0]["increment_uses_count"] == "true"
    now[0] += 2 * 86400
    assert lic.Licensing(tmp_path).tier.key == "supporter" and len(calls) == 1
    now[0] += 86400
    assert lic.Licensing(tmp_path).tier.key == "supporter" and len(calls) == 2
    assert calls[-1]["increment_uses_count"] == "false"
    (tmp_path / "gumroad.json").write_text("[]")
    assert lic.Licensing(tmp_path).tier.key == "supporter" and len(calls) == 3
