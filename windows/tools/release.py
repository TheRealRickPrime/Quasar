"""Package dist\\Quasar into Free / Supporter / Pro zip files under windows\\releases.

Run after build.ps1:   python tools/release.py [--email you@example.com]

The Supporter and Pro zips contain a signed license.key for the given email (default: the owner),
so treat them as private. Only the Free zip is meant for public download; sell keys for the rest.
"""
import argparse
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from make_license import make_key  # noqa: E402
from quasar_win import __version__  # noqa: E402

DIST = ROOT / "dist" / "Quasar"
OUT = ROOT / "releases"
README = """Quasar for Windows {version} - {tier}

Run Quasar.exe (no installer needed). Keep the whole folder together.
{note}
Upgrade or enter a key on the License page inside the app.
"""


def build_zip(tier: str, email: str) -> Path:
    note = {"free": "Free plan: 15 backups and 2 GB of cloud upload per month.",
            "supporter": "Supporter license included (license.key). Unlimited backups, 50 GB/month upload.",
            "pro": "Pro license included (license.key). Unlimited backups and uploads."}[tier]
    target = OUT / f"Quasar-Windows-{tier.capitalize()}-{__version__}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for path in DIST.rglob("*"):
            if path.is_file():
                z.write(path, Path("Quasar") / path.relative_to(DIST))
        z.write(ROOT / "LICENSE.txt", "Quasar/LICENSE.txt")`n        z.writestr("Quasar/README.txt", README.format(version=__version__, tier=tier.capitalize(), note=note))
        if tier != "free":
            z.writestr("Quasar/license.key", make_key(tier, email))
    return target


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", default="owner@quasar.local")
    args = ap.parse_args()
    if not (DIST / "Quasar.exe").exists():
        raise SystemExit("Run build.ps1 first (dist\\Quasar\\Quasar.exe not found).")
    OUT.mkdir(exist_ok=True)
    for tier in ("free", "supporter", "pro"):
        zp = build_zip(tier, args.email)
        print(f"{zp.name}  {zp.stat().st_size / 1e6:.1f} MB")
