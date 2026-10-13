"""Issue license keys (seller only). Keep the private key OUT of the repository.

  python tools/make_license.py --tier pro --email buyer@example.com
  python tools/make_license.py --tier supporter --email a@b.c --expires 2027-12-31 --out license.key

The private key is read from D:\\Quasar-licensing\\private.key or $QUASAR_PRIVATE_KEY.
"""
import argparse
import base64
import json
import os
import secrets
import sys
import time
from pathlib import Path

from cryptography.hazmat.primitives import serialization

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from quasar_win.licensing import TIERS  # noqa: E402

DEFAULT_KEY = Path(os.environ.get("QUASAR_PRIVATE_KEY", r"D:\Quasar-licensing\private.key"))


def make_key(tier: str, email: str, expires: str = "", private_key: Path = DEFAULT_KEY) -> str:
    if tier not in TIERS or tier == "free":
        raise SystemExit("tier must be supporter or pro")
    key = serialization.load_pem_private_key(Path(private_key).read_bytes(), password=None)
    payload = json.dumps({"tier": tier, "email": email, "id": secrets.token_hex(4),
                          "issued": time.strftime("%Y-%m-%d"), "expires": expires},
                         separators=(",", ":")).encode()
    b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()  # noqa: E731
    return f"QSR1.{b64(payload)}.{b64(key.sign(payload))}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", required=True, choices=["supporter", "pro"])
    ap.add_argument("--email", required=True)
    ap.add_argument("--expires", default="")
    ap.add_argument("--out")
    ap.add_argument("--private-key", default=str(DEFAULT_KEY))
    a = ap.parse_args()
    k = make_key(a.tier, a.email, a.expires, Path(a.private_key))
    if a.out:
        Path(a.out).write_text(k, encoding="utf-8")
        print(f"Wrote {a.out}")
    else:
        print(k)
