"""Self-update: read the public manifest, download the new build, verify it and swap it in."""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Callable

import requests

from . import __version__

MANIFEST_URL = "https://quasarli.github.io/latest.json"


class UpdateError(Exception):
    pass


def parse_version(text: str) -> tuple[int, ...]:
    try:
        return tuple(int(p) for p in text.strip().lstrip("v").split("."))
    except ValueError as exc:
        raise UpdateError(f"Bad version number: {text!r}") from exc


def check(current: str = __version__, url: str = MANIFEST_URL) -> dict | None:
    """Return the manifest's Windows entry if it is newer than `current`, else None."""
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        entry = dict(data["windows"])
        entry["version"] = data["version"]
    except (requests.RequestException, ValueError, KeyError) as exc:
        raise UpdateError("Couldn't reach the update server. Check your internet connection.") from exc
    return entry if parse_version(entry["version"]) > parse_version(current) else None


def can_self_update() -> bool:
    return bool(getattr(sys, "frozen", False)) and os.name == "nt"


def download(entry: dict, progress: Callable[[int, int], None] | None = None) -> Path:
    dest = Path(tempfile.mkdtemp(prefix="quasar-update-")) / "update.zip"
    sha = hashlib.sha256()
    try:
        with requests.get(entry["url"], stream=True, timeout=30) as resp:
            resp.raise_for_status()
            total, done = int(resp.headers.get("content-length", 0)), 0
            with open(dest, "wb") as fh:
                for chunk in resp.iter_content(1 << 20):
                    fh.write(chunk)
                    sha.update(chunk)
                    done += len(chunk)
                    if progress:
                        progress(done, total)
    except requests.RequestException as exc:
        raise UpdateError(f"Download failed: {exc}") from exc
    if sha.hexdigest().lower() != entry["sha256"].lower():
        raise UpdateError("The downloaded update failed its integrity check, so it was not installed.")
    return dest


def stage(zip_path: Path) -> Path:
    """Unpack the zip and return the folder that contains Quasar.exe."""
    out = zip_path.parent / "new"
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(out)
    for exe in out.rglob("Quasar.exe"):
        return exe.parent
    raise UpdateError("The update package doesn't contain Quasar.exe.")


def apply_and_restart(new_dir: Path) -> None:
    """Hand off to a script that waits for this process to exit, copies the new files over, relaunches."""
    install = Path(sys.executable).resolve().parent
    script = new_dir.parent / "apply.cmd"
    script.write_text(
        "@echo off\r\n"
        "ping -n 3 127.0.0.1 >nul\r\n"
        f'robocopy "{new_dir}" "{install}" /E /R:10 /W:1 /NFL /NDL /NJH /NJS >nul\r\n'
        f'start "" "{install / "Quasar.exe"}"\r\n'
        f'rmdir /s /q "{new_dir.parent}"\r\n',
        encoding="ascii")
    subprocess.Popen(["cmd", "/c", str(script)], creationflags=0x08000000 | 0x00000008, close_fds=True)
    os._exit(0)
