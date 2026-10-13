"""Settings, on-disk locations and secret storage."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import keyring
from keyring.errors import KeyringError

from . import APP_NAME


def app_dir() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home()))
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def resource_path(*parts: str) -> Path:
    """Locate a bundled asset both from source and from a PyInstaller build."""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return root.joinpath("assets", *parts)


def default_backup_dir() -> Path:
    path = Path.home() / "Documents" / APP_NAME / "Backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


DEFAULTS: dict[str, Any] = {
    "api_base_url": "http://127.0.0.1:8000/api/v1",
    "backup_dir": "",
    "apk_path": "",
    "provider": "local_folder",
    "provider_settings": {},
}


class Settings:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or app_dir() / "settings.json"
        self.data: dict[str, Any] = dict(DEFAULTS)
        if self.path.exists():
            try:
                self.data.update(json.loads(self.path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                pass

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    @property
    def backup_dir(self) -> Path:
        value = self.data.get("backup_dir")
        if value:
            path = Path(value)
            path.mkdir(parents=True, exist_ok=True)
            return path
        return default_backup_dir()


SERVICE = "QuasarWindows"


def store_secret(name: str, value: str) -> bool:
    try:
        keyring.set_password(SERVICE, name, value)
        return True
    except KeyringError:
        return False


def load_secret(name: str) -> str:
    try:
        return keyring.get_password(SERVICE, name) or ""
    except KeyringError:
        return ""
