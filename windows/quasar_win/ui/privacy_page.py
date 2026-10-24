"""Secondary privacy/support surface; never contacts affiliate services itself."""
from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QPushButton, QScrollArea, QVBoxLayout, QWidget

from ..privacy import DELETE_NOTICE, LEGAL_NOTICE
from .context import AppContext
from .widgets import card, label, page_header

AFFILIATES = (
    ("AdGuard", "Optional ad-blocking tools for your browser and devices.",
     "https://adguard.com/?aid=138471"),
    ("AdGuard VPN", "An optional VPN service; not required for a Quasar backup.",
     "https://adguard-vpn.com/?aid=138471"),
    ("AdGuard DNS", "Optional DNS filtering; review the provider's privacy policy and terms.",
     "https://adguard-dns.io/?aid=138471"),
)


class PrivacyPage(QWidget):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.setObjectName("page")
        self.ctx = ctx
        ctx.license_changed.connect(self.refresh)
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        root = QVBoxLayout(content)
        root.addWidget(page_header("Privacy & data", "Your files, your choices. No hosted storage is included."))
        for title, body in (
            ("Local app data",
             "Windows settings, usage counts, history and activated licenses live in "
             "%APPDATA%\\Quasar. Updates and edition changes keep that location. Remove license on the "
             "License page forgets this PC's activation, not your Gumroad purchase or other devices. "
             "Sign out on Account removes the current session, not the server account. To remove local "
             "configuration/history, close Quasar and manage that folder in File Explorer; doing so loses "
             "local settings/activation. Cloud tokens are separate: remove QuasarWindows entries through "
             "Windows Credential Manager and revoke tokens at each provider."),
            ("Backups and cloud copies",
             "Manage backup/image/archive files in their saved folders with File Explorer. Removing app "
             "settings or uninstalling does not remove these files. The guided backup's deletion checkbox "
             "removes its unencrypted original after encryption is verified; temporary compressed "
             "intermediates may also be removed. No secure-wipe feature is provided. Uploaded copies, "
             "cloud trash/version history and synced folders must be managed with their provider, "
             "including any retention policy. Quasar has no cloud-delete or account-deletion API; contact "
             "the operator of your configured optional backend for server records."),
            ("Connections and permissions",
             "Phone access uses ADB after your authorization; imaging needs root/recovery. Cloud uploads "
             "use your configured destination and credentials. Gumroad receives your key when activating "
             "or rechecking (every 3 days, up to 30 days offline). Update checks contact the public release "
             "site only when requested. Affiliate cards load no third-party images, ad SDKs or tracking "
             "requests: an intentional click opens the external provider in your browser. That site's "
             "own cookies, policies and optional paid services then apply."),
            ("Before deleting or overwriting", DELETE_NOTICE + " " + LEGAL_NOTICE),
        ):
            box = card()
            layout = QVBoxLayout(box)
            layout.addWidget(label(title, "h2"))
            layout.addWidget(label(body))
            root.addWidget(box)
        self.affiliates = card()
        offers = QVBoxLayout(self.affiliates)
        offers.addWidget(label("Affiliate recommendations - optional", "h2"))
        offers.addWidget(label(
            "Quasar Labs may earn a commission if you purchase through these links. "
            "No purchase or click is required; recommendations never change your backup allowance. "
            "AdGuard is our primary recommendation. Independent third-party services, not Quasar features."))
        for name, description, url in AFFILIATES:
            offers.addWidget(label(f"<b>{name}</b><br>{description}"))
            button = QPushButton(f"Explore {name} in browser")
            button.clicked.connect(lambda _checked=False, link=url: QDesktopServices.openUrl(QUrl(link)))
            offers.addWidget(button)
        root.addWidget(self.affiliates)
        root.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)
        self.refresh()

    def refresh(self) -> None:
        self.affiliates.setVisible(self.ctx.licensing.show_affiliates)

    def showEvent(self, event) -> None:
        self.refresh()
        super().showEvent(event)
