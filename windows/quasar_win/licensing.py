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

PUBLIC_KEY_B64 = "fPr//U9S+wzVBpzgWc+fJe6HVcHnQuYHxAqe3svBo/s="
PAYPAL_USER = "lircin"
SPONSORS_URL = "https://github.com/sponsors/TheRealRickPrime"
SUPPORT_EMAIL = ""  # where buyers send their PayPal receipt to get a key
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
    def paypal_url(self) -> str:
        return f"https://www.paypal.com/paypalme/{PAYPAL_USER}/{self.price}USD"


TIERS = {
    "free": Tier("free", "Free", 0, 15, 2, "15 backups and 2 GB of cloud upload per month."),
    "supporter": Tier("supporter", "Supporter", 10, None, 50,
                      "Unlimited backups, 50 GB of cloud upload per month."),
    "pro": Tier("pro", "Pro", 25, None, None, "Unlimited backups and cloud upload. One-time payment."),
}


class LicenseError(Exception):
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
    if data.get("tier") not in TIERS or data["tier"] == "free":
        raise LicenseError("License key has an unknown tier.")
    lic = License(data["tier"], data.get("email", ""), data.get("id", ""), data.get("issued", ""),
                  data.get("expires", ""))
    if lic.expires and lic.expires < time.strftime("%Y-%m-%d"):
        raise LicenseError(f"This license expired on {lic.expires}.")
    return lic


def _exe_dir() -> Path:
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent


class Licensing:
    """Current tier plus this month's usage, persisted in %APPDATA%\\Quasar."""

    def __init__(self, directory: Path | None = None, public_key_b64: str = PUBLIC_KEY_B64) -> None:
        self.dir = directory or app_dir()
        self.public_key = public_key_b64
        self.license: License | None = None
        self.problem = ""
        self.reload()

    # ----- license -----
    def reload(self) -> None:
        self.license, self.problem = None, ""
        for path in (self.dir / "license.key", _exe_dir() / "license.key"):
            if path.is_file():
                try:
                    self.license = verify_key(path.read_text(encoding="utf-8"), self.public_key)
                    return
                except (LicenseError, OSError) as exc:
                    self.problem = str(exc)

    def activate(self, key: str) -> License:
        lic = verify_key(key, self.public_key)
        (self.dir / "license.key").write_text(key.strip(), encoding="utf-8")
        self.reload()
        return lic

    def deactivate(self) -> None:
        (self.dir / "license.key").unlink(missing_ok=True)
        self.reload()

    @property
    def tier(self) -> Tier:
        return TIERS[self.license.tier if self.license else "free"]

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
        data = self._usage()
        data["upload_bytes"] += int(size)
        self._save(data)
