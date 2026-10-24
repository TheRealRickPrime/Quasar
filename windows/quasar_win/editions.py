"""Distribution identity is not a paid entitlement."""
from __future__ import annotations

import json
import sys
from enum import Enum
from pathlib import Path


class Edition(str, Enum):
    FREE = "free"
    FREE_ADS = "free-ads"
    SUPPORTER = "supporter"
    PRO = "pro"

    @property
    def label(self) -> str:
        return {
            Edition.FREE: "Free", Edition.FREE_ADS: "Free with Ads",
            Edition.SUPPORTER: "Supporter", Edition.PRO: "Pro",
        }[self]

    @property
    def artifact_label(self) -> str:
        return "Free-with-Ads" if self is Edition.FREE_ADS else self.label


def distribution(directory: Path | None = None) -> Edition:
    directory = directory or (Path(sys.executable).parent if getattr(sys, "frozen", False)
                              else Path(__file__).resolve().parent.parent)
    path = directory / "distribution.json"
    if not path.exists():
        return Edition.FREE
    data = json.loads(path.read_text(encoding="utf-8"))
    return Edition(data["edition"])
