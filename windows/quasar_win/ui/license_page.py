"""License page: current plan, this month's usage, key activation and purchase links."""
from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QHBoxLayout, QLineEdit, QMessageBox, QProgressBar, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from .. import COPYRIGHT, __version__, updater
from .. import licensing as lic
from .context import AppContext
from .widgets import card, fmt_size, label, page_header, set_status


class _UpdateSignals(QObject):
    checked = Signal(object, str)
    progress = Signal(int, int)
    status = Signal(str)


class LicensePage(QWidget):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.setObjectName("page")
        self.ctx = ctx
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        root = QVBoxLayout(content)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        root.addWidget(page_header("License", "Your plan, this month's usage and how to upgrade."))

        plan = card()
        pl = QVBoxLayout(plan)
        self.plan_label = label("")
        self.backup_bar, self.backup_text = QProgressBar(), label("")
        self.upload_bar, self.upload_text = QProgressBar(), label("")
        for w in (self.plan_label, self.backup_text, self.backup_bar, self.upload_text, self.upload_bar):
            pl.addWidget(w)
        root.addWidget(plan)

        key_box = card()
        kl = QVBoxLayout(key_box)
        kl.addWidget(label("<b>Activate a license key</b>"))
        row = QHBoxLayout()
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("License key from your Gumroad receipt")
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.activate_btn = QPushButton("Activate")
        self.activate_btn.setObjectName("primary")
        self.activate_btn.clicked.connect(self._activate)
        self.remove_btn = QPushButton("Remove license")
        self.remove_btn.clicked.connect(self._remove)
        row.addWidget(self.key_edit, 1)
        row.addWidget(self.activate_btn)
        row.addWidget(self.remove_btn)
        self.key_status = label("")
        kl.addLayout(row)
        kl.addWidget(self.key_status)
        root.addWidget(key_box)

        root.addWidget(label(f"Distribution: <b>{ctx.licensing.edition.label}</b>. "
                             "Supporter and Pro packages still require a valid paid key. "
                             "Free without ads remains available. Upload allowance is not hosted storage.", "muted"))
        tiers = QVBoxLayout()
        for tier in lic.TIERS.values():
            box = card()
            bl = QVBoxLayout(box)
            price = "Free" if not tier.price else f"${tier.price}"
            bl.addWidget(label(f"<span style='font-size:15pt'><b>{tier.name}</b></span><br>"
                               f"<span style='font-size:13pt'>{price}</span>"))
            bl.addWidget(label(tier.blurb))
            bl.addStretch()
            if tier.price:
                pay = QPushButton(f"Buy {tier.name} - ${tier.price}")
                pay.setObjectName("primary")
                pay.clicked.connect(lambda _c=False, t=tier: QDesktopServices.openUrl(QUrl(t.buy_url)))
                bl.addWidget(pay)
            tiers.addWidget(box)
        root.addLayout(tiers)

        upd = card()
        ul = QVBoxLayout(upd)
        urow = QHBoxLayout()
        self.update_status = label(f"Quasar {__version__}. Your license and settings carry over when you update.")
        self.update_btn = QPushButton("Check for updates")
        self.update_btn.clicked.connect(self._check_update)
        urow.addWidget(self.update_status, 1)
        urow.addWidget(self.update_btn)
        self.update_bar = QProgressBar()
        self.update_bar.setTextVisible(False)
        self.update_bar.setVisible(False)
        ul.addLayout(urow)
        ul.addWidget(self.update_bar)
        self._upd = _UpdateSignals()
        self._upd.checked.connect(self._on_checked)
        self._upd.progress.connect(self._on_progress)
        self._upd.status.connect(self._on_status)
        root.addWidget(upd)
        self._entry = None

        extra = QHBoxLayout()
        mail = QPushButton("Contact support")
        mail.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(
            f"mailto:{lic.SUPPORT_EMAIL}?subject=Quasar%20support")))
        extra.addWidget(mail)
        extra.addStretch()
        root.addLayout(extra)
        how = ("After buying, Gumroad emails you a license key: paste it above and click Activate. "
               f"Activation needs internet once; questions: <b>{lic.SUPPORT_EMAIL}</b><br>{COPYRIGHT}")
        root.addWidget(label(how, "muted"))
        root.addStretch()
        self.refresh()

    def showEvent(self, event) -> None:
        self.refresh()
        super().showEvent(event)

    def refresh(self) -> None:
        lc = self.ctx.licensing
        tier = lc.tier
        who = f" · {lc.license.email}" if lc.license and lc.license.email else ""
        set_status(self.plan_label, f"Current plan: <b>{tier.name}</b>{who}", "good" if lc.license else "")
        for bar, text, used, limit, fmt in (
                (self.backup_bar, self.backup_text, lc.backups_used, tier.backups_per_month, str),
                (self.upload_bar, self.upload_text, lc.upload_used, lc.upload_limit_bytes, fmt_size)):
            name = "Backups this month" if bar is self.backup_bar else "Cloud upload this month"
            if limit is None:
                text.setText(f"{name}: {fmt(used)} (unlimited)")
                bar.setValue(0)
            else:
                text.setText(f"{name}: {fmt(used)} of {fmt(limit)}")
                bar.setValue(min(int(used * 1000 / limit), 1000))
            bar.setRange(0, 1000)
            bar.setTextVisible(False)
        if lc.problem:
            set_status(self.key_status, lc.problem, "bad")

    def _activate(self) -> None:
        try:
            result = self.ctx.licensing.activate(self.key_edit.text())
        except lic.LicenseError as exc:
            set_status(self.key_status, str(exc), "bad")
            return
        self.key_edit.clear()
        set_status(self.key_status, f"✔ {lic.TIERS[result.tier].name} license activated. Thank you!", "good")
        self.refresh()

    def _check_update(self) -> None:
        if self._entry:
            self._install_update()
            return
        self._busy(True)
        set_status(self.update_status, "Step 1 of 2: contacting the update server…", "")
        threading.Thread(target=self._check_worker, daemon=True).start()

    def _check_worker(self) -> None:
        try:
            self._upd.checked.emit(updater.check(edition=self.ctx.licensing.edition), "")
        except Exception as exc:
            self._upd.checked.emit(None, str(exc) or exc.__class__.__name__)

    def _busy(self, on: bool) -> None:
        self.update_btn.setEnabled(not on)
        self.update_bar.setVisible(on)
        self.update_bar.setRange(0, 0)

    def _on_checked(self, entry, error: str) -> None:
        self._busy(False)
        if error:
            set_status(self.update_status, f"✖ Update check failed: {error}", "bad")
            return
        if not entry:
            self.update_btn.setText("Check for updates")
            set_status(self.update_status, f"✔ Up to date. You have the latest version ({__version__}).", "good")
            return
        if updater.can_self_update():
            self._entry = entry
            self.update_btn.setText(f"Update to {entry['version']} and restart")
            set_status(self.update_status, f"⬆ Version {entry['version']} is available "
                       f"(you have {__version__}). Click the button to install it.", "warn")
        else:
            set_status(self.update_status, f"⬆ Version {entry['version']} is available (you have {__version__}). "
                       "Download it from https://quasarli.github.io. One-click update works in the installed app.",
                       "warn")

    def _install_update(self) -> None:
        entry = self._entry
        self._busy(True)
        self.update_bar.setRange(0, 100)
        self.update_bar.setValue(0)
        set_status(self.update_status, f"Step 2 of 2: downloading version {entry['version']}…", "")
        threading.Thread(target=self._install_worker, args=(entry,), daemon=True).start()

    def _install_worker(self, entry: dict) -> None:
        try:
            zip_path = updater.download(entry, lambda d, t: self._upd.progress.emit(d, t))
            self._upd.status.emit("Verified. Unpacking the update…")
            new_dir = updater.stage(zip_path)
            self._upd.status.emit("Installed. Restarting Quasar…")
            updater.apply_and_restart(new_dir)
        except Exception as exc:
            self._upd.checked.emit(None, str(exc) or exc.__class__.__name__)

    def _on_progress(self, done: int, total: int) -> None:
        if total:
            self.update_bar.setRange(0, 100)
            self.update_bar.setValue(int(done * 100 / total))
        set_status(self.update_status, f"Step 2 of 2: downloading… {fmt_size(done)}"
                   + (f" of {fmt_size(total)}" if total else ""), "")

    def _on_status(self, text: str) -> None:
        self.update_bar.setRange(0, 0)
        set_status(self.update_status, text, "")

    def _remove(self) -> None:
        if QMessageBox.question(self, "Remove local activation?",
                                "This removes the license from this PC, not your Gumroad purchase, "
                                "backups, cloud copies or monthly usage. You can activate it again with "
                                "your receipt key.", QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No) != QMessageBox.Yes:
            return
        self.ctx.licensing.deactivate()
        set_status(self.key_status, f"License removed. Back on the {self.ctx.licensing.tier.name} plan. "
                   "Monthly usage is unchanged.", "")
        self.refresh()
