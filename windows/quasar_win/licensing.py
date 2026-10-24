"""Tiers, offline license keys and monthly usage limits.

A license key is `QSR1.<payload>.<signature>` where the payload is JSON and the signature is Ed25519
over it. The app only holds the public key, so keys cannot be forged without the private key that
stays with the seller (see tools/make_license.py). Limits are enforced client-side, which is an
honest-user system: the source is open, so a determined user can always rebuild without them.
"""
from __future__ import annotations

import base64
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .config import app_dir
from .editions import Edition, distribution

PUBLIC_KEY_B64 = "fPr//U9S+wzVBpzgWc+fJe6HVcHnQuYHxAqe3svBo/s="
SUPPORT_EMAIL = "quasarlabs-inc@outlook.com"
GUMROAD_VERIFY_URL = "https://api.gumroad.com/v2/licenses/verify"
GUMROAD_PRODUCTS = {"qygwf": "supporter", "qwjtj": "pro"}  # Gumroad permalink -> tier
GUMROAD_PRODUCT_IDS = {
    "7sQ_4QWbmr1Miy5LYzh-Bw==": "supporter",
    "9R_AkG7S8By0ZotuYyM1Lg==": "pro",
}
BUY_URLS = {"supporter": "https://quasarlabs3.gumroad.com/l/qygwf",
            "pro": "https://quasarlabs3.gumroad.com/l/qwjtj"}
RECHECK_DAYS, OFFLINE_GRACE_DAYS = 3, 30
GB = 1024 ** 3


@dataclass(frozen=True)
class Tier:
    key: str
    name: str
    price: int
    backups_per_month: int | None   # None = unlimited
    upload_gb_per_month: int | None
    blurb: str

    @property
    def buy_url(self) -> str:
        return BUY_URLS.get(self.key, "")


TIERS = {
    "free": Tier("free", "Free", 0, 6, 2, "6 backups and 2 GB of cloud upload per month."),
    "free-ads": Tier("free-ads", "Free with Ads", 0, 10, 2,
                     "10 backups and 2 GB of cloud upload per month. Optional affiliate recommendations."),
    "supporter": Tier("supporter", "Supporter", 10, 15, 30,
                      "15 backups and 30 GB of cloud upload per month."),
    "pro": Tier("pro", "Pro", 25, None, None, "Unlimited backups and cloud upload. One-time payment."),
}


class LicenseError(Exception):
    pass


class LicenseNetworkError(LicenseError):
    pass


@dataclass
class License:
    tier: str
    email: str
    license_id: str
    issued: str
    expires: str = ""


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def verify_key(key: str, public_key_b64: str = PUBLIC_KEY_B64) -> License:
    parts = key.strip().split(".")
    if len(parts) != 3 or parts[0] != "QSR1":
        raise LicenseError("That doesn't look like a Quasar license key.")
    try:
        payload, sig = _b64d(parts[1]), _b64d(parts[2])
        Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64)).verify(sig, payload)
        data = json.loads(payload)
    except (InvalidSignature, ValueError):
        raise LicenseError("License key is invalid or has been altered.") from None
    if data.get("tier") not in ("supporter", "pro"):
        raise LicenseError("License key has an unknown tier.")
    lic = License(data["tier"], data.get("email", ""), data.get("id", ""), data.get("issued", ""),
                  data.get("expires", ""))
    if lic.expires and lic.expires < time.strftime("%Y-%m-%d"):
        raise LicenseError(f"This license expired on {lic.expires}.")
    return lic


def verify_gumroad(key: str, count_use: bool = False, timeout: float = 10) -> License:
    """Check a Gumroad-issued key against every Quasar product. Needs internet."""
    import requests

    key = key.strip()
    network_error = False
    for product_id, tier in GUMROAD_PRODUCT_IDS.items():
        try:
            def call(field: str, value: str) -> dict:
                response = requests.post(GUMROAD_VERIFY_URL, timeout=timeout, data={
                    field: value, "license_key": key,
                    "increment_uses_count": "true" if count_use else "false"})
                if response.status_code >= 500 or response.status_code == 429:
                    raise requests.ConnectionError("License service unavailable")
                result = response.json()
                if not isinstance(result, dict):
                    raise ValueError("Invalid license response")
                return result
            data = call("product_id", product_id)
        except (requests.RequestException, ValueError):
            network_error = True
            continue
        if data.get("success") is not True:
            continue
        purchase = data.get("purchase", {})
        if not isinstance(purchase, dict):
            network_error = True
            continue
        identities = [
            GUMROAD_PRODUCT_IDS.get(purchase["product_id"]) if purchase.get("product_id") else None,
            GUMROAD_PRODUCTS.get(purchase["short_product_id"]) if purchase.get("short_product_id") else None,
            GUMROAD_PRODUCTS.get(purchase["permalink"]) if purchase.get("permalink") else None,
        ]
        supplied = [v for k, v in zip(("product_id", "short_product_id", "permalink"), identities)
                    if purchase.get(k)]
        if not supplied or any(value != tier for value in supplied):
            continue
        if purchase.get("refunded") or purchase.get("chargebacked") or purchase.get("disputed"):
            raise LicenseError("This purchase was refunded or disputed, so the key is no longer valid.")
        if purchase.get("subscription_cancelled_at") or purchase.get("subscription_failed_at"):
            raise LicenseError("This subscription is no longer active.")
        return License(tier, purchase.get("email", ""), purchase.get("id", "")[:8],
                       time.strftime("%Y-%m-%d"))
    if network_error:
        raise LicenseNetworkError("Couldn't reach the license server. Check your internet connection and try again.")
    raise LicenseError("That license key wasn't found. Check it and try again.")


def _exe_dir() -> Path:
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent


class Licensing:
    """Current tier plus this month's usage, persisted in %APPDATA%\\Quasar."""

    def __init__(self, directory: Path | None = None, public_key_b64: str = PUBLIC_KEY_B64,
                 edition: Edition | None = None) -> None:
        self.dir = directory or app_dir()
        self.dir.mkdir(parents=True, exist_ok=True)
        self.edition = edition if edition is not None else distribution()
        self.public_key = public_key_b64
        self.license: License | None = None
        self._gumroad_checked = 0.0
        self.problem = ""
        self.reload()

    # ----- license -----
    def reload(self) -> None:
        self.problem = ""
        self._gumroad_checked = 0.0
        local = self.dir / "license.key"
        migrated = self.dir / "license-imported"
        paths = (local,) if local.exists() or migrated.exists() else (local, _exe_dir() / "license.key")
        for path in paths:
            if path.is_file():
                try:
                    text = path.read_text(encoding="utf-8").strip()
                    self.license = (verify_key(text, self.public_key) if text.startswith("QSR1.")
                                    else self._cached_gumroad(text))
                    if path != local:
                        local.write_text(text, encoding="utf-8")
                        migrated.touch()
                    return
                except (LicenseError, OSError) as exc:
                    self.problem = str(exc)
        self.license = None

    def _cached_gumroad(self, key: str) -> License:
        """Use the last successful check; re-verify online every few days, tolerate being offline."""
        cache_path = self.dir / "gumroad.json"
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cache = {}
        if (not isinstance(cache, dict) or cache.get("key") != key
                or not isinstance(cache.get("checked"), (int, float))):
            cache = {}
        age = (time.time() - cache.get("checked", 0)) / 86400 if cache else 1e9
        if age < 0:
            age = 1e9
        if age >= RECHECK_DAYS:
            try:
                lic = verify_gumroad(key, timeout=4)
            except LicenseNetworkError:
                if age >= OFFLINE_GRACE_DAYS:
                    raise
            except LicenseError:
                cache_path.unlink(missing_ok=True)
                raise
            else:
                cache = {"key": key, "checked": time.time(), "license": lic.__dict__}
                cache_path.write_text(json.dumps(cache), encoding="utf-8")
        try:
            lic = License(**cache["license"])
        except (KeyError, TypeError) as exc:
            raise LicenseError("The saved license needs online activation again.") from exc
        if lic.tier not in ("supporter", "pro"):
            raise LicenseError("The saved license has an invalid paid tier.")
        self._gumroad_checked = cache["checked"]
        return lic

    def activate(self, key: str) -> License:
        key = key.strip()
        if key.startswith("QSR1."):
            lic = verify_key(key, self.public_key)
        else:
            lic = verify_gumroad(key, count_use=True)
            (self.dir / "gumroad.json").write_text(json.dumps(
                {"key": key, "checked": time.time(), "license": lic.__dict__}), encoding="utf-8")
        (self.dir / "license.key").write_text(key, encoding="utf-8")
        self.reload()
        return lic

    def deactivate(self) -> None:
        (self.dir / "license.key").unlink(missing_ok=True)
        (self.dir / "gumroad.json").unlink(missing_ok=True)
        (self.dir / "license-imported").touch()
        self.reload()

    @property
    def tier(self) -> Tier:
        active = self.license and (self._gumroad_checked == 0 or
                                  0 <= time.time() - self._gumroad_checked < OFFLINE_GRACE_DAYS * 86400)
        return TIERS[self.license.tier if active else
                     ("free-ads" if self.edition is Edition.FREE_ADS else "free")]

    @property
    def show_affiliates(self) -> bool:
        return self.edition is Edition.FREE_ADS and self.tier.key == "free-ads"

    # ----- usage -----
    def _usage(self) -> dict:
        month = time.strftime("%Y-%m")
        try:
            data = json.loads((self.dir / "usage.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        if data.get("month") != month:
            data = {"month": month, "backups": 0, "upload_bytes": 0}
        return data

    def _save(self, data: dict) -> None:
        (self.dir / "usage.json").write_text(json.dumps(data), encoding="utf-8")

    @property
    def backups_used(self) -> int:
        return self._usage()["backups"]

    @property
    def upload_used(self) -> int:
        return self._usage()["upload_bytes"]

    @property
    def upload_limit_bytes(self) -> int | None:
        gb = self.tier.upload_gb_per_month
        return None if gb is None else gb * GB

    def check_backup(self) -> str:
        """Empty string if allowed, else a message explaining the limit."""
        limit = self.tier.backups_per_month
        if limit is not None and self.backups_used >= limit:
            return (f"The {self.tier.name} plan allows {limit} backups a month and you've used them all. "
                    "Upgrade on the License page, or wait until next month.")
        return ""

    def check_upload(self, size: int) -> str:
        if size < 0:
            raise ValueError("Upload size cannot be negative.")
        limit = self.upload_limit_bytes
        if limit is not None and self.upload_used + size > limit:
            left = max(limit - self.upload_used, 0) / GB
            return (f"The {self.tier.name} plan allows {self.tier.upload_gb_per_month} GB of cloud upload a "
                    f"month; {left:.1f} GB left, this upload needs {size / GB:.1f} GB. "
                    "Upgrade on the License page.")
        return ""

    def record_backup(self) -> None:
        data = self._usage()
        data["backups"] += 1
        self._save(data)

    def record_upload(self, size: int) -> None:
        if size < 0:
            raise ValueError("Upload size cannot be negative.")
        data = self._usage()
        data["upload_bytes"] += int(size)
        self._save(data)
