"""Full-image page: back up / restore every partition of a rooted or recovery-booted phone."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLineEdit, QMessageBox,
                               QPlainTextEdit,
                               QProgressBar, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget,
                               QVBoxLayout, QWidget)

from .. import compression, image
from ..config import app_dir
from .context import AppContext
from .widgets import card, fmt_size, label, page_header, run_task, set_status

GUIDE = (
    "<b>Choose how the phone gives Quasar raw access to its storage:</b><br>"
    "<b>A · Custom recovery (best):</b> boot TWRP or similar. Nothing is mounted, so the image is exactly "
    "consistent and every partition can be restored. Needs an unlocked bootloader; use "
    "<i>Boot recovery image…</i> to boot one temporarily without flashing it.<br>"
    "<b>B · Magisk (phone stays on):</b> grant the 'Shell' superuser prompt. Quasar pauses Android, "
    "syncs, remounts /data read-only, images, then resumes. System partitions can only be restored from recovery."
    "<br><span style='color:#ffb454'>Encrypted /data is imaged as-is: it only unlocks on the same phone, so "
    "keep <b>metadata</b> and <b>persist</b> selected.</span>")


class ImagePage(QWidget):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.setObjectName("page")
        self.ctx = ctx
        self.access: image.Access | None = None
        self.parts: list[image.Partition] = []
        self.manifest: dict | None = None
        self.task = None
        self.busy = False
        root = QVBoxLayout(self)
        root.addWidget(page_header("Full Phone Image",
                                   "Byte-exact partition images that can be written back to rebuild the phone."))
        info = card()
        il = QVBoxLayout(info)
        il.addWidget(label(GUIDE))
        self.device_status = label("")
        self.access_status = label("")
        row = QHBoxLayout()
        self.detect_btn = QPushButton("Check root access")
        self.detect_btn.setObjectName("primary")
        self.detect_btn.clicked.connect(self._detect)
        self.recovery_btn = QPushButton("Reboot to recovery")
        self.recovery_btn.clicked.connect(self._reboot_recovery)
        self.boot_btn = QPushButton("Boot recovery image…")
        self.boot_btn.clicked.connect(self._boot_image)
        for b in (self.detect_btn, self.recovery_btn, self.boot_btn):
            row.addWidget(b)
        row.addStretch()
        il.addWidget(self.device_status)
        il.addWidget(self.access_status)
        il.addLayout(row)
        root.addWidget(info)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_tab(), "Create image")
        self.tabs.addTab(self._restore_tab(), "Restore image")
        root.addWidget(self.tabs, 1)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(110)
        self.progress = QProgressBar()
        root.addWidget(self.progress)
        root.addWidget(self.log)
        ctx.devices_changed.connect(self._refresh)
        self._refresh()

    # ----- tabs -----
    def _table(self, headers: list[str]) -> QTableWidget:
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.verticalHeader().setVisible(False)
        t.horizontalHeader().setStretchLastSection(True)
        t.setSelectionMode(QTableWidget.NoSelection)
        return t

    def _sync_levels(self) -> None:
        levels = compression.METHODS[self.comp_method.currentData()].levels
        keep = self.comp_level.currentData()
        self.comp_level.clear()
        for lv in compression.LEVEL_ORDER:
            if lv in levels:
                self.comp_level.addItem(lv.capitalize(), lv)
        i = self.comp_level.findData(keep)
        self.comp_level.setCurrentIndex(i if i >= 0 else self.comp_level.count() - 1)

    def _apply_saved_compression(self) -> None:
        saved = (self.ctx.settings.get("compression_method"), self.ctx.settings.get("compression_level"))
        if saved == getattr(self, "_applied", None):
            return
        self._applied = saved
        method = saved[0]
        i = self.comp_method.findData(method)
        if i < 0:
            return
        self.comp_method.setCurrentIndex(i)
        self._sync_levels()
        j = self.comp_level.findData(self.ctx.settings.get("compression_level"))
        if j >= 0:
            self.comp_level.setCurrentIndex(j)

    def showEvent(self, event) -> None:  # noqa: N802
        self._apply_saved_compression()
        super().showEvent(event)

    def _create_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.table = self._table(["Image", "Partition", "Type", "Size"])
        self.table.itemChanged.connect(self._update_total)
        opts = QHBoxLayout()
        self.compress_box = QCheckBox("Compress")
        self.compress_box.setChecked(True)
        self.comp_method = QComboBox()
        for key in image.IMAGE_METHODS:
            self.comp_method.addItem(compression.METHODS[key].label, key)
        self.comp_level = QComboBox()
        for lv in compression.LEVEL_ORDER:
            self.comp_level.addItem(lv.capitalize(), lv)
        self.comp_method.currentIndexChanged.connect(self._sync_levels)
        self.compress_box.toggled.connect(self.comp_method.setEnabled)
        self.compress_box.toggled.connect(self.comp_level.setEnabled)
        self._apply_saved_compression()
        self.quiesce_box = QCheckBox("Freeze Android + read-only /data (Magisk mode)")
        self.quiesce_box.setChecked(True)
        self.upload_box = QCheckBox("Upload to cloud afterwards")
        self.enc_pass = QLineEdit()
        self.enc_pass.setEchoMode(QLineEdit.Password)
        self.enc_pass.setPlaceholderText("Encryption passphrase (8+ chars, blank = upload unencrypted)")
        self.total = label("")
        opts.addWidget(self.compress_box)
        opts.addWidget(self.comp_method)
        opts.addWidget(self.comp_level)
        opts.addWidget(self.quiesce_box)
        opts.addWidget(self.upload_box)
        opts.addStretch()
        opts.addWidget(self.total)
        dest = QHBoxLayout()
        self.dest = QLineEdit(self.ctx.settings.get("image_dir") or str(Path(app_dir()).parent / "Quasar Images"))
        browse = QPushButton("Browse…")
        browse.clicked.connect(lambda: self._pick_dir(self.dest))
        dest.addWidget(label("Save to"))
        dest.addWidget(self.dest, 1)
        dest.addWidget(browse)
        buttons = QHBoxLayout()
        self.start_btn = QPushButton("Create full image")
        self.start_btn.setObjectName("primary")
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self._start_image)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(lambda: self.task and self.task.cancel.set())
        buttons.addWidget(self.start_btn)
        buttons.addWidget(self.cancel_btn)
        buttons.addStretch()
        lay.addWidget(self.table, 1)
        lay.addLayout(opts)
        lay.addWidget(self.enc_pass)
        lay.addLayout(dest)
        lay.addLayout(buttons)
        return w

    def _restore_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        row = QHBoxLayout()
        self.src = QLineEdit()
        self.src.setPlaceholderText("Folder containing quasar-image.json")
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._pick_image)
        row.addWidget(self.src, 1)
        row.addWidget(browse)
        self.rtable = self._table(["Restore", "Partition", "Type", "Size", "Stored"])
        self.rinfo = label("")
        self.bootchain_box = QCheckBox("Also allow bootloader-chain partitions (can brick the phone)")
        self.confirm = QLineEdit()
        self.confirm.setPlaceholderText("Type RESTORE to confirm. This overwrites the phone's partitions.")
        self.confirm.textChanged.connect(self._restore_enabled)
        buttons = QHBoxLayout()
        self.verify_btn = QPushButton("Verify image files")
        self.verify_btn.setEnabled(False)
        self.verify_btn.clicked.connect(self._verify)
        self.restore_btn = QPushButton("Restore to phone")
        self.restore_btn.setObjectName("primary")
        self.restore_btn.setEnabled(False)
        self.restore_btn.clicked.connect(self._start_restore)
        self.upload_btn = QPushButton("Upload this image to cloud")
        self.upload_btn.setEnabled(False)
        self.upload_btn.clicked.connect(lambda: self._upload(Path(self.src.text())))
        buttons.addWidget(self.verify_btn)
        buttons.addWidget(self.upload_btn)
        buttons.addWidget(self.restore_btn)
        buttons.addStretch()
        for item in (row, self.rinfo, self.rtable, self.bootchain_box, self.confirm, buttons):
            lay.addWidget(item) if isinstance(item, QWidget) else lay.addLayout(item)
        return w

    # ----- device / access -----
    def _serial(self) -> str:
        return self.ctx.device.serial if self.ctx.device else ""

    def _refresh(self, *_a) -> None:
        device = self.ctx.device
        set_status(self.device_status, f"Phone: <b>{device.title}</b>" if device else
                   "No phone connected (USB debugging on, or recovery booted).", "" if device else "warn")
        for b in (self.detect_btn, self.recovery_btn):
            b.setEnabled(bool(device) and not self.busy)
        self.boot_btn.setEnabled(self.ctx.adb.available)
        if not device:
            self.access = None
            self.parts = []
            self._fill_parts()
            set_status(self.access_status, "", "")
        self._restore_enabled()

    def _detect(self) -> None:
        serial, adb = self._serial(), self.ctx.adb
        self.detect_btn.setEnabled(False)
        set_status(self.access_status, "Checking… approve the superuser prompt on the phone if it appears.", "")

        def work(_r, _c):
            access = image.detect_access(adb, serial)
            return access, image.list_partitions(adb, serial, access)

        def done(result):
            self.access, self.parts = result
            self.quiesce_box.setEnabled(self.access.live)
            set_status(self.access_status, f"✔ Access: <b>{self.access.label}</b>, {len(self.parts)} partitions found.", "good")
            self._fill_parts()
            self._refresh()

        def failed(msg):
            self.access = None
            set_status(self.access_status, msg, "bad")
            self._refresh()

        run_task(work, on_done=done, on_failed=failed)

    def _reboot_recovery(self) -> None:
        run_task(lambda _r, _c: self.ctx.adb.reboot(self._serial(), "recovery"),
                 on_done=lambda _x: self.log.appendPlainText("Rebooting to recovery. Wait for it to appear, then check root access."),
                 on_failed=lambda m: self.log.appendPlainText(f"Failed: {m}"))

    def _boot_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Recovery image for your phone", "", "Images (*.img)")
        if not path:
            return
        self.log.appendPlainText("Put the phone in bootloader mode first (adb reboot bootloader). Booting recovery image…")
        run_task(lambda _r, _c: self.ctx.adb.fastboot_boot(Path(path)),
                 on_done=lambda out: self.log.appendPlainText(out or "Recovery booted."),
                 on_failed=lambda m: self.log.appendPlainText(f"Failed: {m}"))

    # ----- create -----
    def _fill_parts(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.parts))
        for i, p in enumerate(self.parts):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Checked if p.selected else Qt.Unchecked)
            self.table.setItem(i, 0, chk)
            for c, text in enumerate((p.name, p.kind, fmt_size(p.size)), 1):
                self.table.setItem(i, c, QTableWidgetItem(text))
        self.table.blockSignals(False)
        self.table.resizeColumnsToContents()
        self._update_total()

    def _chosen(self) -> list[image.Partition]:
        return [p for i, p in enumerate(self.parts) if self.table.item(i, 0).checkState() == Qt.Checked]

    def _update_total(self, *_a) -> None:
        chosen = self._chosen() if self.parts else []
        size = sum(p.size for p in chosen)
        set_status(self.total, f"{len(chosen)} selected · {fmt_size(size)} raw" if chosen else "", "")
        self.start_btn.setEnabled(bool(chosen and self.access and not self.busy))

    def _pick_dir(self, edit: QLineEdit) -> None:
        d = QFileDialog.getExistingDirectory(self, "Choose folder", edit.text())
        if d:
            edit.setText(d)

    def _busy(self, busy: bool) -> None:
        self.busy = busy
        self.cancel_btn.setEnabled(busy)
        if not busy:
            self.task = None
            self.progress.setValue(0)
        self.start_btn.setEnabled(not busy and bool(self.access))
        self._refresh()
        self._update_total()

    def _on_progress(self, fraction: float, text: str) -> None:
        self.progress.setValue(int(fraction * 1000))
        self.progress.setFormat(text)

    def _start_image(self) -> None:
        chosen, access, adb, serial = self._chosen(), self.access, self.ctx.adb, self._serial()
        if not (chosen and access):
            return
        if any(p.kind == "data" for p in chosen) and access.live and self.quiesce_box.isChecked():
            if QMessageBox.question(self, "Pause Android?",
                                    "The phone's screen will freeze while /data is imaged and Android resumes afterwards. Continue?"
                                    ) != QMessageBox.Yes:
                return
        self.ctx.settings.set("image_dir", self.dest.text())
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = Path(self.dest.text()) / f"{(self.ctx.device.title if self.ctx.device else 'phone').replace(' ', '_')}-{stamp}"
        compress, quiesce = self.compress_box.isChecked(), self.quiesce_box.isChecked()
        method, level_name = self.comp_method.currentData(), self.comp_level.currentData()
        upload = self.upload_box.isChecked()
        limit_msg = self.ctx.licensing.check_backup()
        if limit_msg:
            self.log.appendPlainText(limit_msg)
            return
        if upload and not self._upload_ready():
            return
        total = sum(p.size for p in chosen) or 1
        self._busy(True)
        self.log.appendPlainText(f"Imaging {len(chosen)} partitions to {out}")

        offsets, running = {}, 0
        for p in chosen:
            offsets[p.name] = running
            running += p.size

        def work(report, cancel):
            return image.create_image(
                adb, serial, access, chosen, out, compress=compress, method=method, level_name=level_name,
                quiesce=quiesce, cancel=cancel,
                on_progress=lambda n, d, s, r: report((offsets[n] + d) / total,
                                                      f"{n}  {fmt_size(d)}/{fmt_size(s)}  {fmt_size(r)}/s"),
                log=lambda m: report(-1, m))

        def prog(frac, text):
            if frac < 0:
                self.log.appendPlainText(text)
            else:
                self._on_progress(frac, text)

        def done(manifest):
            data = image.load_manifest(manifest.parent)
            stored = sum(r["stored_size"] for r in data["partitions"])
            self.log.appendPlainText(f"✔ Image complete ({data['consistency']}), {fmt_size(stored)} on disk: {manifest.parent}")
            self._busy(False)
            self.ctx.licensing.record_backup()
            if upload:
                self._upload(manifest.parent)

        self.task = run_task(work, on_progress=prog, on_done=done,
                             on_failed=lambda m: (self.log.appendPlainText(f"Failed: {m}"), self._busy(False)))

    # ----- upload -----
    def _upload_ready(self) -> bool:
        if self.ctx.provider() is None:
            self.log.appendPlainText("Set up a cloud destination on the Cloud Upload page first.")
            return False
        if self.enc_pass.text() and len(self.enc_pass.text()) < 8:
            self.log.appendPlainText("Passphrase must be at least 8 characters.")
            return False
        return True

    def _upload(self, folder: Path) -> None:
        if not self._upload_ready():
            return
        provider, phrase = self.ctx.provider(), self.enc_pass.text()
        size = sum(p.stat().st_size for p in folder.iterdir() if p.is_file())
        limit_msg = self.ctx.licensing.check_upload(size)
        if limit_msg:
            self.log.appendPlainText(limit_msg)
            return
        self._busy(True)
        self.log.appendPlainText(f"Uploading to {provider.label}{' (encrypted)' if phrase else ' (UNENCRYPTED)'}…")
        self.task = run_task(
            lambda report, cancel: image.upload_image(folder, provider, phrase, on_progress=report, cancel=cancel),
            on_progress=self._on_progress,
            on_done=lambda locs: (self.ctx.licensing.record_upload(size),
                                  self.log.appendPlainText(f"✔ Uploaded {len(locs)} files."), self._busy(False)),
            on_failed=lambda m: (self.log.appendPlainText(f"Upload failed: {m}"), self._busy(False)))

    # ----- restore -----
    def _pick_image(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Choose image folder", self.dest.text())
        if not d:
            return
        self.src.setText(d)
        try:
            self.manifest = image.load_manifest(Path(d))
        except (image.ImageError, OSError, ValueError) as exc:
            self.manifest = None
            set_status(self.rinfo, str(exc), "bad")
            self.rtable.setRowCount(0)
            self._restore_enabled()
            return
        dev = self.manifest["device"]
        set_status(self.rinfo, f"Image of <b>{dev.get('brand', '')} {dev.get('model', '')}</b> "
                   f"({dev.get('device', '?')}), taken {self.manifest['created'][:16]}, "
                   f"{self.manifest['consistency']}.", "")
        recs = self.manifest["partitions"]
        self.rtable.setRowCount(len(recs))
        for i, r in enumerate(recs):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Unchecked if r["kind"] == "bootchain" else Qt.Checked)
            self.rtable.setItem(i, 0, chk)
            for c, text in enumerate((r["name"], r["kind"], fmt_size(r["size"]), fmt_size(r["stored_size"])), 1):
                self.rtable.setItem(i, c, QTableWidgetItem(text))
        self.rtable.resizeColumnsToContents()
        self._restore_enabled()

    def _restore_enabled(self, *_a) -> None:
        ready = bool(self.manifest and not self.busy)
        self.verify_btn.setEnabled(ready)
        self.upload_btn.setEnabled(ready)
        self.restore_btn.setEnabled(ready and bool(self.access) and self.confirm.text().strip() == "RESTORE")

    def _restore_names(self) -> list[str]:
        recs = self.manifest["partitions"] if self.manifest else []
        return [r["name"] for i, r in enumerate(recs) if self.rtable.item(i, 0).checkState() == Qt.Checked]

    def _verify(self) -> None:
        folder, names = Path(self.src.text()), self._restore_names()
        recs = [r for r in self.manifest["partitions"] if r["name"] in names]
        self._busy(True)
        self.log.appendPlainText("Verifying stored image files…")

        def work(report, cancel):
            bad = []
            for i, rec in enumerate(recs):
                report(i / len(recs), f"Checking {rec['name']}")
                if not image.verify_record(folder, rec, cancel):
                    bad.append(rec["name"])
            return bad

        self.task = run_task(
            work, on_progress=self._on_progress,
            on_done=lambda bad: (self.log.appendPlainText("✔ All files match their checksums." if not bad else
                                                          f"✖ Corrupt: {', '.join(bad)}"), self._busy(False)),
            on_failed=lambda m: (self.log.appendPlainText(f"Failed: {m}"), self._busy(False)))

    def _start_restore(self) -> None:
        folder, names, access = Path(self.src.text()), self._restore_names(), self.access
        adb, serial, allow = self.ctx.adb, self._serial(), self.bootchain_box.isChecked()
        if not (names and access):
            return
        from ..privacy import DELETE_NOTICE, LEGAL_NOTICE
        if QMessageBox.question(self, "Overwrite phone partitions?",
                                f"Restore will overwrite {', '.join(names)} on the selected phone. "
                                "Existing data in those partitions can be lost.\n\n" + DELETE_NOTICE +
                                "\n\n" + LEGAL_NOTICE, QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No) != QMessageBox.Yes:
            return
        self._busy(True)
        self.log.appendPlainText(f"Restoring {', '.join(names)} (access: {access.label})")

        def work(report, cancel):
            return image.restore_image(
                adb, serial, access, folder, names, allow_bootchain=allow, cancel=cancel,
                on_progress=lambda n, d, s, r: report(d / max(s, 1), f"{n}  {fmt_size(d)}/{fmt_size(s)}  {fmt_size(r)}/s"),
                log=lambda m: report(-1, m))

        def prog(frac, text):
            self.log.appendPlainText(text) if frac < 0 else self._on_progress(frac, text)

        def done(restored):
            self.log.appendPlainText(f"✔ Restored and read-back verified: {', '.join(restored)}. Reboot the phone.")
            self.confirm.clear()
            self._busy(False)

        self.task = run_task(work, on_progress=prog, on_done=done,
                             on_failed=lambda m: (self.log.appendPlainText(f"Failed: {m}"), self._busy(False)))
