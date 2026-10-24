"""Guided ADB backup wizard."""
from __future__ import annotations

import os
import time
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLineEdit,
                               QProgressBar, QPushButton, QStackedWidget, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView, QMessageBox)

from .. import adb as adb_mod
from .. import compression
from .. import encryption
from ..cloud import make_provider
from ..config import load_secret
from ..pipeline import PipelineOptions, run_pipeline
from ..privacy import DELETE_NOTICE, LEGAL_NOTICE
from .context import AppContext
from .widgets import card, fmt_size, fmt_time, label, page_header, run_task, set_status

STEPS = ["Tools", "Phone", "Connect", "Options", "Backup", "Finish"]


class BackupWizard(QWidget):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.setObjectName("page")
        self.ctx = ctx
        self.raw_path: Path | None = None
        self.backup_task = None
        self.pipeline_task = None
        self.backup_ok = False
        self.pipeline_done = False

        root = QVBoxLayout(self)
        root.addWidget(page_header(
            "Guided backup",
            "Quasar walks you through every step. Your phone stays in control: you approve the backup on its screen."))
        self.crumbs = label("", "subtitle", wrap=False)
        root.addWidget(self.crumbs)
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        for build in (self._tools_page, self._phone_page, self._connect_page,
                      self._options_page, self._backup_page, self._finish_page):
            self.stack.addWidget(build())

        nav = QHBoxLayout()
        self.back_btn = QPushButton("Back")
        self.next_btn = QPushButton("Next")
        self.next_btn.setObjectName("primary")
        self.back_btn.clicked.connect(lambda: self.go(self.stack.currentIndex() - 1))
        self.next_btn.clicked.connect(lambda: self.go(self.stack.currentIndex() + 1))
        nav.addWidget(self.back_btn)
        nav.addStretch()
        nav.addWidget(self.next_btn)
        root.addLayout(nav)

        ctx.devices_changed.connect(self._refresh_connect)
        ctx.adb_changed.connect(self._refresh_tools)
        self.go(0)

    # ---------- navigation ----------
    def go(self, index: int) -> None:
        index = max(0, min(index, len(STEPS) - 1))
        self.stack.setCurrentIndex(index)
        parts = [f"<b style='color:#46E1FF'>{i + 1}. {n}</b>" if i == index
                 else f"<span style='color:#8A8F98'>{i + 1}. {n}</span>" for i, n in enumerate(STEPS)]
        self.crumbs.setText("  &nbsp;›&nbsp;  ".join(parts))
        self.back_btn.setEnabled(index > 0 and not self._busy())
        self.next_btn.setVisible(index < len(STEPS) - 1)
        if index == 0:
            self._refresh_tools()
        elif index == 2:
            self.ctx.poll()
            self._refresh_connect()
        elif index == 3:
            self._refresh_options()
        self._update_next()

    def _busy(self) -> bool:
        return bool(self.backup_task and getattr(self, "_backup_running", False)) or \
            bool(getattr(self, "_pipeline_running", False))

    def _update_next(self) -> None:
        i = self.stack.currentIndex()
        ok = {
            0: self.ctx.adb.available,
            1: all(c.isChecked() for c in self.checks),
            2: self.ctx.device is not None,
            3: self._options_valid(),
            4: self.backup_ok and not self._backup_running,
        }.get(i, False)
        self.next_btn.setEnabled(bool(ok))
        self.back_btn.setEnabled(i > 0 and not self._busy())

    # ---------- step 1: tools ----------
    def _tools_page(self) -> QWidget:
        w, lay = self._panel("Step 1 · Android platform-tools",
                             "ADB (Android Debug Bridge) is the official Google tool that talks to your phone over USB.")
        self.adb_status = label("", wrap=True)
        self.dl_bar = QProgressBar()
        self.dl_bar.setVisible(False)
        row = QHBoxLayout()
        self.dl_btn = QPushButton("Download platform-tools from Google")
        self.dl_btn.setObjectName("primary")
        self.dl_btn.clicked.connect(self._download_adb)
        browse = QPushButton("I already have adb.exe…")
        browse.clicked.connect(self._browse_adb)
        row.addWidget(self.dl_btn)
        row.addWidget(browse)
        row.addStretch()
        lay.addWidget(self.adb_status)
        lay.addWidget(self.dl_bar)
        lay.addLayout(row)
        lay.addStretch()
        return w

    def _refresh_tools(self) -> None:
        if self.ctx.adb.available:
            set_status(self.adb_status, f"✔ ADB found: {self.ctx.adb.path}", "good")
            self.dl_btn.setText("Re-download latest platform-tools")
        else:
            set_status(self.adb_status, "ADB is not installed yet. Quasar can download Google's official "
                       "platform-tools (about 8 MB) into your user profile.", "warn")
        self._update_next()

    def _download_adb(self) -> None:
        self.dl_btn.setEnabled(False)
        self.dl_bar.setVisible(True)
        self.dl_bar.setValue(0)
        run_task(lambda report, _c: adb_mod.download_platform_tools(lambda f: report(f, "")),
                 on_progress=lambda f, _t: self.dl_bar.setValue(int(f * 100)),
                 on_done=self._adb_downloaded, on_failed=self._adb_failed)

    def _adb_downloaded(self, _path) -> None:
        self.dl_btn.setEnabled(True)
        self.dl_bar.setVisible(False)
        self.ctx.reload_adb()
        self.ctx.start_server()

    def _adb_failed(self, message: str) -> None:
        self.dl_btn.setEnabled(True)
        self.dl_bar.setVisible(False)
        set_status(self.adb_status, f"Download failed: {message}. Check your connection or pick adb.exe manually.", "bad")

    def _browse_adb(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select adb.exe", "", "adb.exe (adb.exe)")
        if path:
            os.environ["PATH"] = str(Path(path).parent) + os.pathsep + os.environ.get("PATH", "")
            self.ctx.reload_adb()

    # ---------- step 2: phone prep ----------
    def _phone_page(self) -> QWidget:
        w, lay = self._panel("Step 2 · Prepare your phone",
                             "Tick each item once you have done it on the phone.")
        steps = [
            ("Open <b>Settings → About phone</b> and tap <b>Build number</b> 7 times until it says "
             "“You are now a developer”."),
            "Open <b>Settings → System → Developer options</b> and turn on <b>USB debugging</b>.",
            "In Developer options also turn on <b>Stay awake</b> so the screen doesn't lock mid-backup.",
            "Unlock the phone and connect it to this PC with a data-capable USB cable "
            "(choose <b>File transfer</b> if the phone asks).",
        ]
        self.checks = []
        for text in steps:
            box = QCheckBox()
            lab = label(text)
            row = QHBoxLayout()
            row.addWidget(box, 0, Qt.AlignTop)
            row.addWidget(lab, 1)
            box.toggled.connect(lambda _=None: self._update_next())
            self.checks.append(box)
            lay.addLayout(row)
        lay.addStretch()
        return w

    # ---------- step 3: connect ----------
    def _connect_page(self) -> QWidget:
        w, lay = self._panel("Step 3 · Connect and authorise",
                             "Quasar watches for your phone live; no refresh needed.")
        self.conn_title = label("", "h2")
        self.conn_text = label("")
        self.conn_warn = label("", "warn")
        self.device_pick = QComboBox()
        self.device_pick.currentIndexChanged.connect(self._device_picked)
        lay.addWidget(self.conn_title)
        lay.addWidget(self.conn_text)
        lay.addWidget(self.device_pick)
        lay.addWidget(self.conn_warn)
        lay.addStretch()
        return w

    def _refresh_connect(self, *_args) -> None:
        devices = self.ctx.devices
        self.device_pick.blockSignals(True)
        self.device_pick.clear()
        ready = [d for d in devices if d.ready]
        for d in ready:
            self.device_pick.addItem(f"{d.title}  ·  Android {d.android}  ·  {d.serial}", d.serial)
        self.device_pick.setVisible(len(ready) > 1)
        self.device_pick.blockSignals(False)
        device = self.ctx.device
        if device:
            set_status(self.conn_title, f"✔ Connected: {device.title}", "h2")
            set_status(self.conn_text, f"Android {device.android} (API {device.sdk}) · serial {device.serial}", "good")
            self.conn_warn.setText(device.backup_warning)
        else:
            self.conn_warn.setText("")
            unauthorised = [d for d in devices if d.state == "unauthorized"]
            offline = [d for d in devices if d.state == "offline"]
            if unauthorised:
                set_status(self.conn_title, "Waiting for you to allow this computer", "h2")
                set_status(self.conn_text, "Look at your phone: tap <b>Allow</b> on “Allow USB debugging?” "
                           "(tick <i>Always allow from this computer</i>). If nothing appears, unplug and "
                           "replug, or use <b>Developer options → Revoke USB debugging authorisations</b>.", "warn")
            elif offline:
                set_status(self.conn_title, "Phone is offline", "h2")
                set_status(self.conn_text, "Unplug and replug the cable, then unlock the phone.", "warn")
            elif not self.ctx.adb.available:
                set_status(self.conn_title, "ADB missing", "h2")
                set_status(self.conn_text, "Go back to step 1 to install platform-tools.", "bad")
            else:
                set_status(self.conn_title, "No phone detected yet", "h2")
                set_status(self.conn_text, self.ctx.device_error or
                           "Plug in the phone and unlock it. Try a different cable or port if it doesn't "
                           "appear: some cables only charge.", "")
        self._update_next()

    def _device_picked(self) -> None:
        self.ctx.selected_serial = self.device_pick.currentData() or ""
        self._refresh_connect()

    # ---------- step 4: options ----------
    def _apply_saved_compression(self) -> None:
        saved = (self.ctx.settings.get("compression_method"), self.ctx.settings.get("compression_level"))
        if saved == getattr(self, "_applied", None):
            return
        self._applied = saved
        method = saved[0]
        i = self.comp_method.findData(method) if method else -1
        if i >= 0:
            self.comp_method.setCurrentIndex(i)
            j = self.comp_level.findData(self.ctx.settings.get("compression_level"))
            if j >= 0:
                self.comp_level.setCurrentIndex(j)

    def showEvent(self, event) -> None:  # noqa: N802
        if self.stack.currentIndex() == 0 or not self.backup_task:
            self._apply_saved_compression()
        super().showEvent(event)

    def _options_page(self) -> QWidget:
        w, lay = self._panel("Step 4 · Choose what to back up and how to protect it", "")
        self.opt_apk = QCheckBox("Include app APKs (bigger, but restores apps themselves)")
        self.opt_shared = QCheckBox("Include shared storage (photos, downloads, media)")
        self.opt_shared.setChecked(True)
        self.opt_system = QCheckBox("Include system apps")
        for c in (self.opt_apk, self.opt_shared, self.opt_system):
            lay.addWidget(c)

        form = QHBoxLayout()
        self.comp_method = QComboBox()
        self.comp_method.addItem("No extra compression", "")
        for m in compression.METHODS.values():
            self.comp_method.addItem(f"{m.label}  -  {m.note}", m.key)
        self.comp_level = QComboBox()
        for lv in compression.LEVEL_ORDER:
            self.comp_level.addItem(lv.capitalize(), lv)
        self.comp_level.setCurrentIndex(1)
        form.addWidget(label("Compression"))
        form.addWidget(self.comp_method, 1)
        form.addWidget(self.comp_level)
        lay.addLayout(form)
        lay.addWidget(label("Tip: adb backups are already deflate-compressed, so gains are usually small. "
                            "Use the <b>Compression Lab</b> to measure on your own data.", "muted"))
        self._apply_saved_compression()

        self.enc_check = QCheckBox("Encrypt the backup before it leaves this PC (recommended)")
        self.enc_check.setChecked(True)
        self.enc_level = QComboBox()
        for key, text in encryption.SECURITY_LEVELS.items():
            self.enc_level.addItem(text, key)
        self.enc_level.setCurrentIndex(1)
        self.pass1 = QLineEdit()
        self.pass1.setEchoMode(QLineEdit.Password)
        self.pass1.setPlaceholderText("Passphrase (cannot be recovered if lost)")
        self.pass2 = QLineEdit()
        self.pass2.setEchoMode(QLineEdit.Password)
        self.pass2.setPlaceholderText("Repeat passphrase")
        self.delete_raw = QCheckBox("Delete the unencrypted original once the encrypted copy is verified")
        self.delete_raw.setChecked(True)
        for wdg in (self.enc_check, self.enc_level, self.pass1, self.pass2, self.delete_raw):
            lay.addWidget(wdg)
        lay.addWidget(label("Deletion is not secure erase. Preserve legally required records. "
                            "See Privacy & data for local/cloud deletion details.", "muted"))
        self.enc_check.toggled.connect(self._enc_toggled)

        self.upload_check = QCheckBox("Upload to cloud when finished")
        self.upload_note = label("", "muted")
        lay.addWidget(self.upload_check)
        lay.addWidget(self.upload_note)

        folder = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setReadOnly(True)
        pick = QPushButton("Change…")
        pick.clicked.connect(self._pick_folder)
        folder.addWidget(label("Save to"))
        folder.addWidget(self.folder_edit, 1)
        folder.addWidget(pick)
        lay.addLayout(folder)
        lay.addStretch()
        for sig in (self.pass1.textChanged, self.pass2.textChanged, self.enc_check.toggled):
            sig.connect(lambda *_: self._update_next())
        return w

    def _enc_toggled(self, on: bool) -> None:
        for wdg in (self.enc_level, self.pass1, self.pass2, self.delete_raw):
            wdg.setEnabled(on)

    def _refresh_options(self) -> None:
        self.folder_edit.setText(str(self.ctx.settings.backup_dir))
        key = self.ctx.settings.get("provider")
        provider = self._provider()
        if provider is None:
            self.upload_check.setChecked(False)
            self.upload_check.setEnabled(False)
            self.upload_note.setText("Set up a destination on the <b>Cloud</b> page to enable uploads.")
        else:
            self.upload_check.setEnabled(True)
            self.upload_note.setText(f"Destination: <b>{provider.label}</b> (change on the Cloud page)")

    def _provider(self):
        key = self.ctx.settings.get("provider")
        cfg = dict(self.ctx.settings.get("provider_settings", {}).get(key, {}))
        from ..cloud import PROVIDERS
        if key not in PROVIDERS:
            return None
        for f in PROVIDERS[key].fields:
            if f.secret:
                cfg[f.key] = load_secret(f"{key}.{f.key}")
        if not any(cfg.values()):
            return None
        return make_provider(key, cfg)

    def _pick_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose backup folder", self.folder_edit.text())
        if path:
            self.ctx.settings.set("backup_dir", path)
            self.folder_edit.setText(path)

    def _options_valid(self) -> bool:
        if not hasattr(self, "enc_check") or not self.enc_check.isChecked():
            return True
        return len(self.pass1.text()) >= 8 and self.pass1.text() == self.pass2.text()

    # ---------- step 5: backup ----------
    _backup_running = False
    _pipeline_running = False

    def _backup_page(self) -> QWidget:
        w, lay = self._panel("Step 5 · Run the backup",
                             "This step needs you and your phone.")
        lay.addWidget(label(
            "<b>When you press Start:</b><br>"
            "1. Keep the phone <b>unlocked</b> and plugged in.<br>"
            "2. A <b>“Full backup”</b> screen appears on the phone. Optionally set a password for the "
            "backup there.<br>"
            "3. Tap <b>Back up my data</b>. Don't unplug until Quasar says it's finished."))
        self.bk_status = label("Ready.", "muted")
        self.bk_bar = QProgressBar()
        self.bk_bar.setRange(0, 0)
        self.bk_bar.setVisible(False)
        row = QHBoxLayout()
        self.bk_start = QPushButton("Start backup")
        self.bk_start.setObjectName("primary")
        self.bk_cancel = QPushButton("Cancel")
        self.bk_cancel.setEnabled(False)
        self.bk_start.clicked.connect(self._start_backup)
        self.bk_cancel.clicked.connect(lambda: self.backup_task and self.backup_task.cancel.set())
        row.addWidget(self.bk_start)
        row.addWidget(self.bk_cancel)
        row.addStretch()
        lay.addWidget(self.bk_status)
        lay.addWidget(self.bk_bar)
        lay.addLayout(row)
        lay.addStretch()
        return w

    def _start_backup(self) -> None:
        device = self.ctx.device
        if not device:
            set_status(self.bk_status, "Phone disconnected. Go back to the Connect step.", "bad")
            return
        limit_msg = self.ctx.licensing.check_backup()
        if limit_msg:
            set_status(self.bk_status, limit_msg, "bad")
            return
        stamp = time.strftime("%Y%m%d-%H%M%S")
        safe = "".join(ch if ch.isalnum() else "_" for ch in device.title)
        self.raw_path = self.ctx.settings.backup_dir / f"quasar-{safe}-{stamp}.ab"
        self._backup_running, self.backup_ok = True, False
        self.bk_start.setEnabled(False)
        self.bk_cancel.setEnabled(True)
        self.bk_bar.setVisible(True)
        set_status(self.bk_status, "<b>Now look at your phone</b> and tap <b>Back up my data</b>…", "warn")
        opts = (self.opt_apk.isChecked(), self.opt_shared.isChecked(), self.opt_system.isChecked())
        raw, serial, adb = self.raw_path, device.serial, self.ctx.adb

        def work(report, cancel):
            return adb.run_backup(raw, serial, *opts,
                                  lambda size, secs: report(size, f"{secs:.1f}"), cancel)

        def progress(size: float, secs: str) -> None:
            if size > 1024:
                elapsed = float(secs)
                set_status(self.bk_status, f"Backing up… {fmt_size(size)} received · {fmt_time(elapsed)} · "
                           f"{fmt_size(size / max(elapsed, 0.1))}/s", "")

        self.backup_task = run_task(work, on_progress=progress, on_done=self._backup_done,
                                    on_failed=self._backup_failed)
        self._update_next()

    def _backup_done(self, outcome) -> None:
        self._backup_running = False
        self.bk_bar.setVisible(False)
        self.bk_cancel.setEnabled(False)
        self.bk_start.setEnabled(True)
        problem = outcome.verdict()
        if problem:
            set_status(self.bk_status, f"⚠ {problem}<br>Size received: {fmt_size(outcome.size)}. "
                       "Press Start to try again.", "bad")
            self.backup_ok = False
        else:
            self.ctx.licensing.record_backup()
            set_status(self.bk_status, f"✔ Backup complete: {fmt_size(outcome.size)} in "
                       f"{fmt_time(outcome.seconds)}.", "good")
            self.backup_ok = True
        self._update_next()

    def _backup_failed(self, message: str) -> None:
        self._backup_running = False
        self.bk_bar.setVisible(False)
        self.bk_cancel.setEnabled(False)
        self.bk_start.setEnabled(True)
        set_status(self.bk_status, f"Backup failed: {message}", "bad")
        self._update_next()

    # ---------- step 6: finish ----------
    def _finish_page(self) -> QWidget:
        w, lay = self._panel("Step 6 · Compress, encrypt and upload", "")
        self.pl_status = label("Press Process to apply your choices.", "muted")
        self.pl_bar = QProgressBar()
        self.pl_bar.setRange(0, 1000)
        self.pl_table = QTableWidget(0, 5)
        self.pl_table.setHorizontalHeaderLabels(["Stage", "In", "Out", "Time", "Details"])
        self.pl_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.pl_table.verticalHeader().setVisible(False)
        self.pl_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.pl_table.setMaximumHeight(190)
        row = QHBoxLayout()
        self.pl_start = QPushButton("Process backup")
        self.pl_start.setObjectName("primary")
        self.pl_cancel = QPushButton("Cancel")
        self.pl_cancel.setEnabled(False)
        self.pl_open = QPushButton("Open folder")
        self.pl_new = QPushButton("Start another")
        self.pl_start.clicked.connect(self._start_pipeline)
        self.pl_cancel.clicked.connect(lambda: self.pipeline_task and self.pipeline_task.cancel.set())
        self.pl_open.clicked.connect(lambda: self.raw_path and os.startfile(self.raw_path.parent))
        self.pl_new.clicked.connect(self._reset)
        for b in (self.pl_start, self.pl_cancel, self.pl_open, self.pl_new):
            row.addWidget(b)
        row.addStretch()
        self.pl_warn = label("", "warn")
        for item in (self.pl_status, self.pl_bar, self.pl_table, self.pl_warn):
            lay.addWidget(item)
        lay.addLayout(row)
        lay.addStretch()
        return w

    def _start_pipeline(self) -> None:
        if not self.raw_path or not self.raw_path.exists():
            set_status(self.pl_status, "The backup file is missing.", "bad")
            return
        provider = self._provider() if self.upload_check.isChecked() else None
        if provider is not None:
            limit_msg = self.ctx.licensing.check_upload(self.raw_path.stat().st_size)
            if limit_msg:
                set_status(self.pl_status, limit_msg, "bad")
                return
        encrypt = self.enc_check.isChecked()
        if encrypt and self.delete_raw.isChecked():
            if QMessageBox.question(self, "Remove the unencrypted original?",
                                    f"The unencrypted original at {self.raw_path} will be deleted after "
                                    "the encrypted copy is verified. This does not delete cloud copies.\n\n"
                                    + DELETE_NOTICE + "\n\n" + LEGAL_NOTICE,
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
        opts = PipelineOptions(
            compression=self.comp_method.currentData() or "", level=self.comp_level.currentData(),
            passphrase=self.pass1.text() if encrypt else "", security=self.enc_level.currentData(),
            delete_original=self.delete_raw.isChecked(), provider=provider)
        raw, history = self.raw_path, self.ctx.history
        self._pipeline_running = True
        self.pl_start.setEnabled(False)
        self.pl_cancel.setEnabled(True)
        self.back_btn.setEnabled(False)
        self.pl_table.setRowCount(0)
        self.pl_warn.setText("")
        self.pipeline_task = run_task(
            lambda report, cancel: run_pipeline(raw, opts, report, cancel, history),
            on_progress=lambda f, t: (self.pl_bar.setValue(int(f * 1000)), set_status(self.pl_status, t, "")),
            on_done=self._pipeline_done, on_failed=self._pipeline_failed)

    def _pipeline_done(self, result) -> None:
        self._pipeline_running = False
        self.pl_cancel.setEnabled(False)
        self.pl_start.setEnabled(False)
        self.raw_path = result.final_path
        for st in result.stages:
            if st.name.startswith("Upload"):
                self.ctx.licensing.record_upload(st.output_size)
            r = self.pl_table.rowCount()
            self.pl_table.insertRow(r)
            for c, text in enumerate((st.name, fmt_size(st.input_size), fmt_size(st.output_size),
                                      fmt_time(st.seconds), st.detail)):
                self.pl_table.setItem(r, c, QTableWidgetItem(text))
        extra = ""
        if result.upload_location:
            extra = f"<br>Uploaded to {result.upload_location}"
        set_status(self.pl_status, f"✔ Finished. Final file: {result.final_path}{extra}", "good")
        self.pl_warn.setText("<br>".join(result.warnings))
        self._record_session(result)
        self.back_btn.setEnabled(True)

    def _record_session(self, result) -> None:
        if not self.ctx.api.logged_in:
            return
        device = self.ctx.device
        api, provider = self.ctx.api, self.ctx.settings.get("provider")

        def work(_r, _c):
            api.create_session(provider, device.title if device else "Android device", str(result.final_path))

        run_task(work)

    def _pipeline_failed(self, message: str) -> None:
        self._pipeline_running = False
        self.pl_cancel.setEnabled(False)
        self.pl_start.setEnabled(True)
        self.back_btn.setEnabled(True)
        set_status(self.pl_status, f"Stopped: {message}. Your original backup file is untouched "
                   "unless a verified encrypted copy was made.", "bad")

    def _reset(self) -> None:
        self.backup_ok = False
        self.raw_path = None
        self.pl_start.setEnabled(True)
        self.pl_table.setRowCount(0)
        self.pl_bar.setValue(0)
        set_status(self.bk_status, "Ready.", "muted")
        set_status(self.pl_status, "Press Process to apply your choices.", "muted")
        self.go(0)

    # ---------- helpers ----------
    def _panel(self, title: str, subtitle: str):
        outer = QWidget()
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        frame = card()
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(22, 18, 22, 18)
        lay.setSpacing(10)
        lay.addWidget(label(title, "h2"))
        if subtitle:
            lay.addWidget(label(subtitle, "muted"))
        outer_lay.addWidget(frame)
        return outer, lay
