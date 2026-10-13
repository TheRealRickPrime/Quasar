"""Persistent log of compression and upload runs, used for comparisons."""
from __future__ import annotations

import json
import time
from typing import Any

from .config import app_dir


class History:
    def __init__(self) -> None:
        self.path = app_dir() / "history.json"

    def all(self) -> list[dict[str, Any]]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []

    def add(self, kind: str, **fields: Any) -> None:
        records = self.all()
        records.append({"kind": kind, "when": time.time(), **fields})
        self.path.write_text(json.dumps(records[-500:], indent=2), encoding="utf-8")

    def of_kind(self, kind: str) -> list[dict[str, Any]]:
        return [r for r in self.all() if r.get("kind") == kind]
