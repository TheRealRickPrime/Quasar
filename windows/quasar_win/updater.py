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
from urllib.parse import urlparse

import requests

from . import __version__
from .editions import Edition, distribution

MANIFEST_URL = "https://quasarli.github.io/latest.json"


class UpdateError(Exception):
    pass


def parse_version(text: str) -> tuple[int, ...]:
    try:
        return tuple(int(p) for p in text.strip().lstrip("v").split("."))
    except ValueError as exc:
        raise UpdateError(f"Bad version number: {text!r}") from exc


def parse_manifest(data: dict, current: str, edition: Edition) -> dict | None:
    try:
        platform = data["windows"]
        if "editions" in platform:
            entry = dict(platform["editions"][edition.value])
            entry["version"] = entry.get("version", platform.get("version"))
        elif data.get("schemaVersion", 1) == 1 and edition is Edition.FREE:
            entry = dict(platform)
            entry["version"] = platform.get("version", data.get("version"))
        else:
            raise UpdateError("No update is published for this distribution yet.")
        parsed = urlparse(entry["url"])
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("An HTTPS download URL is required")
        digest = entry["sha256"]
        if len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest):
            raise ValueError("Invalid SHA256")
        return entry if parse_version(entry["version"]) > parse_version(current) else None
    except (KeyError, TypeError, ValueError) as exc:
        raise UpdateError("The update manifest is invalid or missing this distribution.") from exc


def check(current: str = __version__, url: str = MANIFEST_URL,
          edition: Edition | None = None) -> dict | None:
    """Return the manifest's Windows entry if it is newer than `current`, else None."""
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise UpdateError("Couldn't reach the update server. Check your internet connection.") from exc
    return parse_manifest(data, current, edition if edition is not None else distribution())


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
        dest.unlink(missing_ok=True)
        raise UpdateError("The downloaded update failed its integrity check, so it was not installed.")
    return dest


def stage(zip_path: Path) -> Path:
    """Unpack the zip and return the folder that contains Quasar.exe."""
    out = zip_path.parent / "new"
    with zipfile.ZipFile(zip_path) as zf:
        for item in zf.infolist():
            path = Path(item.filename)
            if (path.is_absolute() or ".." in path.parts or ":" in item.filename
                    or "\\" in item.filename or (item.external_attr >> 16) & 0o170000 == 0o120000):
                raise UpdateError("The update contains an unsafe archive path.")
            if path.name.lower() in {"license.key", "gumroad.json", "usage.json", "settings.json",
                                     "private.key"}:
                raise UpdateError("The update must not replace personal license or settings data.")
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
