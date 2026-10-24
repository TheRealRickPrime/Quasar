"""Install the Quasar Android app (.apk) on the connected phone."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from ..config import resource_path
from .context import AppContext
from .widgets import card, fmt_size, label, page_header, run_task, set_status


class AppPage(QWidget):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.setObjectName("page")
        self.ctx = ctx
        root = QVBoxLayout(self)
        root.addWidget(page_header("Quasar for Android",
                                   "Install the Quasar phone app straight from this PC over ADB."))
        box = card()
        lay = QVBoxLayout(box)
        self.apk_status = label("")
        row = QHBoxLayout()
        self.path = QLineEdit(ctx.settings.get("apk_path"))
        self.path.setPlaceholderText("Path to quasar.apk")
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        row.addWidget(self.path, 1)
        row.addWidget(browse)
        self.device_status = label("")
        self.install_btn = QPushButton("Install on phone")
        self.install_btn.setObjectName("primary")
        self.install_btn.clicked.connect(self._install)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(150)
        for item in (self.apk_status, row, self.device_status):
            lay.addWidget(item) if isinstance(item, QWidget) else lay.addLayout(item)
        lay.addWidget(self.install_btn)
        lay.addWidget(self.log)
        root.addWidget(box)
        root.addStretch()
        self.path.textChanged.connect(self._refresh)
        ctx.devices_changed.connect(self._refresh)
        self._refresh()

    def _apk(self) -> Path | None:
        typed = self.path.text().strip()
        if typed and Path(typed).is_file():
            return Path(typed)
        label = self.ctx.licensing.edition.artifact_label
        bundled = sorted(resource_path("apk").glob(f"Quasar-Android-{label}-*.apk"))
        if not bundled:
            bundled = sorted(resource_path("apk").glob("*.apk")) if resource_path("apk").exists() else []
        return bundled[-1] if bundled else None

    def _refresh(self, *_a) -> None:
        apk = self._apk()
        if apk:
            set_status(self.apk_status, f"✔ APK ready: {apk.name} ({fmt_size(apk.stat().st_size)})", "good")
        else:
            set_status(self.apk_status, "No APK found. Drop it into "
                       "<code>windows\\assets\\apk\\</code> before packaging, or browse to it here.", "warn")
        device = self.ctx.device
        set_status(self.device_status, f"Target phone: <b>{device.title}</b>" if device else
                   "No phone connected. Use the Backup page to connect one.", "" if device else "warn")
        self.install_btn.setEnabled(bool(apk and device))

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select APK", "", "Android package (*.apk)")
        if path:
            self.path.setText(path)
            self.ctx.settings.set("apk_path", path)

    def _install(self) -> None:
        apk, device, adb = self._apk(), self.ctx.device, self.ctx.adb
        if not apk or not device:
            return
        self.install_btn.setEnabled(False)
        self.log.appendPlainText(f"Installing {apk.name} on {device.title}…")
        run_task(lambda _r, _c: adb.install_apk(apk, device.serial),
                 on_done=lambda out: (self.log.appendPlainText(out), self._refresh()),
                 on_failed=lambda m: (self.log.appendPlainText(f"Failed: {m}"), self._refresh()))
