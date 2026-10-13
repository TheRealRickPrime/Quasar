"""License page: current plan, this month's usage, key activation and purchase links."""
from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QProgressBar, QPushButton, QVBoxLayout, QWidget

from .. import licensing as lic
from .context import AppContext
from .widgets import card, fmt_size, label, page_header, set_status


class LicensePage(QWidget):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.setObjectName("page")
        self.ctx = ctx
        root = QVBoxLayout(self)
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
        self.key_edit.setPlaceholderText("QSR1.…")
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

        tiers = QHBoxLayout()
        for tier in lic.TIERS.values():
            box = card()
            bl = QVBoxLayout(box)
            price = "Free" if not tier.price else f"${tier.price}"
            bl.addWidget(label(f"<span style='font-size:15pt'><b>{tier.name}</b></span><br>"
                               f"<span style='font-size:13pt'>{price}</span>"))
            bl.addWidget(label(tier.blurb))
            bl.addStretch()
            if tier.price:
                pay = QPushButton(f"Pay ${tier.price} with PayPal")
                pay.setObjectName("primary")
                pay.clicked.connect(lambda _c=False, t=tier: QDesktopServices.openUrl(QUrl(t.paypal_url)))
                bl.addWidget(pay)
            tiers.addWidget(box)
        root.addLayout(tiers)

        extra = QHBoxLayout()
        sponsor = QPushButton("Sponsor on GitHub (free to set up, no fees)")
        sponsor.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(lic.SPONSORS_URL)))
        extra.addWidget(sponsor)
        extra.addStretch()
        root.addLayout(extra)
        how = ("After paying, include your email in the PayPal note"
               + (f" and send the receipt to <b>{lic.SUPPORT_EMAIL}</b>" if lic.SUPPORT_EMAIL else
                  " and contact the developer with the receipt")
               + ". You'll get a key to paste above. Keys work offline and are tied to no device.")
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

    def _remove(self) -> None:
        self.ctx.licensing.deactivate()
        set_status(self.key_status, "License removed. Back on the Free plan.", "")
        self.refresh()
