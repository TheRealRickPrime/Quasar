"""Cloud destinations, uploads and upload-speed comparison."""
from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

from PySide6.QtWidgets import (QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLineEdit, QProgressBar,
                               QPushButton, QScrollArea, QVBoxLayout, QWidget)

from ..cloud import PROVIDERS, UploadError, make_provider
from ..config import app_dir, load_secret, store_secret
from .context import AppContext
from .widgets import BarChart, card, fmt_size, fmt_time, label, page_header, run_task, set_status


class CloudPage(QWidget):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.setObjectName("page")
        self.ctx = ctx
        self.task = None
        self.inputs: dict[str, QLineEdit] = {}

        inner = QWidget()
        inner.setObjectName("page")
        root = QVBoxLayout(inner)
        root.addWidget(page_header("Cloud upload",
                                   "Choose where encrypted backups go, then compare how fast each destination is."))

        dest = card()
        dl = QVBoxLayout(dest)
        dl.addWidget(label("Destination", "h2"))
        self.provider = QComboBox()
        for key, cls in PROVIDERS.items():
            self.provider.addItem(cls.label, key)
        self.provider.setCurrentIndex(max(self.provider.findData(ctx.settings.get("provider")), 0))
        self.provider.currentIndexChanged.connect(self._rebuild_form)
        self.help = label("", "muted")
        self.form = QFormLayout()
        dl.addWidget(self.provider)
        dl.addWidget(self.help)
        dl.addLayout(self.form)
        row = QHBoxLayout()
        save = QPushButton("Save")
        save.setObjectName("primary")
        test = QPushButton("Test connection")
        save.clicked.connect(self._save)
        test.clicked.connect(self._test)
        row.addWidget(save)
        row.addWidget(test)
        row.addStretch()
        dl.addLayout(row)
        self.status = label("", "muted")
        dl.addWidget(self.status)
        dl.addWidget(label("Tokens and keys are stored in Windows Credential Manager, not in plain text.", "muted"))
        root.addWidget(dest)

        up = card()
        ul = QVBoxLayout(up)
        ul.addWidget(label("Upload & measure", "h2"))
        frow = QHBoxLayout()
        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("File to upload (e.g. an encrypted .qsr backup)")
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        frow.addWidget(self.file_edit, 1)
        frow.addWidget(browse)
        ul.addLayout(frow)
        brow = QHBoxLayout()
        self.upload_btn = QPushButton("Upload file")
        self.upload_btn.setObjectName("primary")
        self.test_size = QComboBox()
        for mb in (5, 25, 100):
            self.test_size.addItem(f"{mb} MB random test payload", mb)
        self.speed_btn = QPushButton("Run speed test")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.upload_btn.clicked.connect(self._upload_file)
        self.speed_btn.clicked.connect(self._speed_test)
        self.cancel_btn.clicked.connect(lambda: self.task and self.task.cancel.set())
        for wdg in (self.upload_btn, self.test_size, self.speed_btn, self.cancel_btn):
            brow.addWidget(wdg)
        brow.addStretch()
        ul.addLayout(brow)
        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.up_status = label("", "muted")
        ul.addWidget(self.bar)
        ul.addWidget(self.up_status)
        root.addWidget(up)

        cmp_card = card()
        cl = QVBoxLayout(cmp_card)
        self.speed_chart = BarChart("Average upload speed by destination, Mbit/s (higher is better)", False)
        self.recent_chart = BarChart("Most recent uploads, Mbit/s", False)
        cl.addWidget(self.speed_chart)
        cl.addWidget(self.recent_chart)
        root.addWidget(cmp_card)
        root.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(inner)
        scroll.viewport().setAutoFillBackground(False)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        self._rebuild_form()
        self.refresh_charts()

    @property
    def key(self) -> str:
        return self.provider.currentData()

    def _rebuild_form(self) -> None:
        while self.form.rowCount():
            self.form.removeRow(0)
        self.inputs.clear()
        cls = PROVIDERS[self.key]
        self.help.setText(cls.help)
        saved = self.ctx.settings.get("provider_settings", {}).get(self.key, {})
        for f in cls.fields:
            edit = QLineEdit()
            edit.setPlaceholderText(f.placeholder)
            if f.secret:
                edit.setEchoMode(QLineEdit.Password)
                edit.setText(load_secret(f"{self.key}.{f.key}"))
            else:
                edit.setText(saved.get(f.key, ""))
            self.inputs[f.key] = edit
            self.form.addRow(f.label, edit)

    def _config(self) -> dict[str, str]:
        return {k: v.text().strip() for k, v in self.inputs.items()}

    def _save(self) -> None:
        cls = PROVIDERS[self.key]
        plain = {f.key: self.inputs[f.key].text().strip() for f in cls.fields if not f.secret}
        all_settings = dict(self.ctx.settings.get("provider_settings", {}))
        all_settings[self.key] = plain
        self.ctx.settings.data["provider_settings"] = all_settings
        self.ctx.settings.set("provider", self.key)
        failed = [f.label for f in cls.fields if f.secret
                  and not store_secret(f"{self.key}.{f.key}", self.inputs[f.key].text().strip())]
        if failed:
            set_status(self.status, "Saved, but Windows Credential Manager refused: " + ", ".join(failed), "bad")
        else:
            set_status(self.status, f"✔ Saved. {cls.label} is now the backup destination.", "good")

    def _test(self) -> None:
        provider = make_provider(self.key, self._config())
        set_status(self.status, "Testing…", "")
        run_task(lambda _r, _c: provider.test(),
                 on_done=lambda msg: set_status(self.status, f"✔ {msg}", "good"),
                 on_failed=lambda msg: set_status(self.status, f"✖ {msg}", "bad"))

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose file", str(self.ctx.settings.backup_dir))
        if path:
            self.file_edit.setText(path)

    def _busy(self, on: bool) -> None:
        for b in (self.upload_btn, self.speed_btn):
            b.setEnabled(not on)
        self.cancel_btn.setEnabled(on)

    def _upload_file(self) -> None:
        path = Path(self.file_edit.text().strip())
        if not path.is_file():
            set_status(self.up_status, "Choose a file first.", "bad")
            return
        self._start_upload(path, test=False, cleanup=False)

    def _speed_test(self) -> None:
        size = self.test_size.currentData() * 1024 * 1024
        path = app_dir() / f"quasar-speedtest-{self.test_size.currentData()}MB.bin"
        path.write_bytes(os.urandom(size))
        self._start_upload(path, test=True, cleanup=True)

    def _start_upload(self, path: Path, test: bool, cleanup: bool) -> None:
        provider = make_provider(self.key, self._config())
        if not test:
            limit_msg = self.ctx.licensing.check_upload(path.stat().st_size)
            if limit_msg:
                set_status(self.up_status, limit_msg, "bad")
                return
        self._busy(True)
        set_status(self.up_status, f"Uploading {path.name} to {provider.label}…", "")

        def work(report, cancel):
            try:
                return provider.upload(path, lambda s, t: report(s / t if t else 1, f"{fmt_size(s)} of {fmt_size(t)}"),
                                       cancel)
            finally:
                if cleanup:
                    path.unlink(missing_ok=True)

        def done(result):
            self._busy(False)
            self.bar.setValue(1000)
            if not test:
                self.ctx.licensing.record_upload(result.size)
            self.ctx.history.add("upload", provider=result.provider, size=result.size,
                                 seconds=result.seconds, speed_mbps=result.speed_mbps, test=test)
            set_status(self.up_status, f"✔ {fmt_size(result.size)} in {fmt_time(result.seconds)} · "
                       f"{result.speed_mbps:.1f} Mbit/s ({result.speed_mb_s:.2f} MB/s)", "good")
            self.refresh_charts()

        def failed(message):
            self._busy(False)
            set_status(self.up_status, f"✖ {message}", "bad")

        self.task = run_task(work, on_progress=lambda f, t: (self.bar.setValue(int(f * 1000)),
                                                              set_status(self.up_status, t, "")),
                             on_done=done, on_failed=failed)

    def refresh_charts(self) -> None:
        records = self.ctx.history.of_kind("upload")
        grouped = defaultdict(list)
        for r in records:
            if r.get("speed_mbps"):
                grouped[r["provider"]].append(r["speed_mbps"])
        rows = [(PROVIDERS[p].label if p in PROVIDERS else p, sum(v) / len(v), f"{sum(v) / len(v):.1f} Mbit/s")
                for p, v in grouped.items()]
        self.speed_chart.set_rows(rows)
        recent = [(f"{PROVIDERS[r['provider']].label if r['provider'] in PROVIDERS else r['provider']} · "
                   f"{fmt_size(r['size'])}", r["speed_mbps"], f"{r['speed_mbps']:.1f} Mbit/s")
                  for r in records[-6:][::-1] if r.get("speed_mbps")]
        self.recent_chart.set_rows(recent)
