"""Package dist\\Quasar into Free / Supporter / Pro zip files under windows\\releases.

Run after build.ps1:   python tools/release.py

  Quasar-Windows-<ver>.zip        no key inside. Upload to Gumroad (Supporter + Pro) and share publicly:
                                  it runs as Free until a key is activated.
  Quasar-Windows-OWNER-<ver>.zip  contains a Pro license.key for you. Keep it private.
"""
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
README = """Quasar for Windows {version}

Run Quasar.exe (no installer needed). Keep the whole folder together.
Free plan: 15 backups and 2 GB of cloud upload per month.
Bought Supporter or Pro? Open the License page, paste the key from your Gumroad receipt and click Activate.
"""


def build_zip(owner: bool) -> Path:
    target = OUT / f"Quasar-Windows-{'OWNER-' if owner else ''}{__version__}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for path in DIST.rglob("*"):
            if path.is_file():
                z.write(path, Path("Quasar") / path.relative_to(DIST))
        z.write(ROOT / "LICENSE.txt", "Quasar/LICENSE.txt")
        z.writestr("Quasar/README.txt", README.format(version=__version__))
        if owner:
            z.writestr("Quasar/license.key", make_key("pro", "owner@quasar.local"))
    return target


if __name__ == "__main__":
    if not (DIST / "Quasar.exe").exists():
        raise SystemExit("Run build.ps1 first (dist\\Quasar\\Quasar.exe not found).")
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.zip"):
        old.unlink()
    for owner in (False, True):
        zp = build_zip(owner)
        print(f"{zp.name}  {zp.stat().st_size / 1e6:.1f} MB")
