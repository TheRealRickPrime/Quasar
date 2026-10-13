"""Home dashboard."""
from __future__ import annotations

import time

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from .context import AppContext
from .widgets import card, fmt_size, fmt_time, label, page_header, set_status


class HomePage(QWidget):
    navigate = Signal(int)

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.setObjectName("page")
        self.ctx = ctx
        root = QVBoxLayout(self)
        root.addWidget(page_header("Welcome to Quasar",
                                   "Privacy-first Android backup: guided, encrypted, and measured."))
        status = card()
        sl = QVBoxLayout(status)
        sl.addWidget(label("Phone", "h2"))
        self.adb_line = label("")
        self.device_line = label("")
        sl.addWidget(self.adb_line)
        sl.addWidget(self.device_line)
        root.addWidget(status)

        actions = QHBoxLayout()
        for text, page, primary in (("Start guided backup", 1, True), ("Compression Lab", 2, False),
                                    ("Cloud upload", 3, False), ("Install Android app", 5, False)):
            b = QPushButton(text)
            b.setObjectName("primary" if primary else "")
            b.clicked.connect(lambda _=None, p=page: self.navigate.emit(p))
            actions.addWidget(b)
        actions.addStretch()
        root.addLayout(actions)

        recent = card()
        rl = QVBoxLayout(recent)
        rl.addWidget(label("Recent activity", "h2"))
        self.activity = label("")
        rl.addWidget(self.activity)
        root.addWidget(recent)
        root.addStretch()
        ctx.devices_changed.connect(self.refresh)
        ctx.adb_changed.connect(self.refresh)
        self.refresh()

    def refresh(self, *_a) -> None:
        if self.ctx.adb.available:
            set_status(self.adb_line, "✔ ADB ready", "good")
        else:
            set_status(self.adb_line, "ADB not installed. The guided backup will download it for you.", "warn")
        device = self.ctx.device
        if device:
            set_status(self.device_line, f"✔ {device.title} · Android {device.android}", "good")
        else:
            set_status(self.device_line, "No phone connected", "muted")
        lines = []
        for r in self.ctx.history.all()[-5:][::-1]:
            when = time.strftime("%b %d %H:%M", time.localtime(r["when"]))
            if r["kind"] == "upload":
                lines.append(f"{when} · Upload via {r['provider']} · {fmt_size(r['size'])} · "
                             f"{r['speed_mbps']:.1f} Mbit/s")
            else:
                lines.append(f"{when} · Compress {r['method']} ({r['level']}) · "
                             f"{fmt_size(r['original'])} → {fmt_size(r['compressed'])} in {fmt_time(r['seconds'])}")
        self.activity.setText("<br>".join(lines) or "Nothing yet. Start with a guided backup.")
