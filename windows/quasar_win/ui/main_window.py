"""Main window and application entry point."""
from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QMainWindow, QStackedWidget, QVBoxLayout, QWidget)

from .. import APP_NAME, __version__
from ..config import resource_path
from . import theme
from .account_page import AccountPage
from .app_page import AppPage
from .backup_page import BackupWizard
from .cloud_page import CloudPage
from .context import AppContext
from .home_page import HomePage
from .image_page import ImagePage
from .lab_page import LabPage
from .license_page import LicensePage
from .privacy_page import PrivacyPage
from .widgets import SpaceBackground

NAV = ["◉  Home", "⬡  Guided Backup", "◈  Compression Lab", "☁  Cloud Upload", "☺  Account", "▣  Android App",
       "✦  Full Phone Image", "★  License", "Privacy & data"]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} for Windows")
        self.setWindowIcon(QIcon(str(resource_path("quasar.ico"))))
        self.resize(1180, 780)
        self.setMinimumSize(980, 660)
        self.ctx = AppContext()

        background = SpaceBackground()
        self.setCentralWidget(background)
        layout = QHBoxLayout(background)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(230)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(0, 18, 0, 12)
        logo = QLabel()
        logo.setPixmap(QPixmap(str(resource_path("quasar.png"))).scaled(
            84, 84, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.setAlignment(Qt.AlignCenter)
        name = QLabel(APP_NAME.upper())
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet("font-size: 16pt; font-weight: 700; letter-spacing: 6px;")
        tag = QLabel("secure Android backup")
        tag.setAlignment(Qt.AlignCenter)
        tag.setObjectName("muted")
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setIconSize(QSize(0, 0))
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for text in NAV:
            self.nav.addItem(QListWidgetItem(text))
        version = QLabel(f"v{__version__} · {self.ctx.licensing.edition.label}")
        version.setObjectName("muted")
        version.setAlignment(Qt.AlignCenter)
        for item in (logo, name, tag):
            sl.addWidget(item)
        sl.addSpacing(16)
        sl.addWidget(self.nav, 1)
        sl.addWidget(version)
        layout.addWidget(side)

        self.pages = QStackedWidget()
        self.home = HomePage(self.ctx)
        self.home.navigate.connect(self.nav.setCurrentRow)
        self.cloud = CloudPage(self.ctx)
        for page in (self.home, BackupWizard(self.ctx), LabPage(self.ctx), self.cloud,
                     AccountPage(self.ctx), AppPage(self.ctx), ImagePage(self.ctx), LicensePage(self.ctx),
                     PrivacyPage(self.ctx)):
            self.pages.addWidget(page)
        holder = QWidget()
        hl = QVBoxLayout(holder)
        hl.setContentsMargins(26, 22, 26, 18)
        hl.addWidget(self.pages)
        layout.addWidget(holder, 1)

        self.nav.currentRowChanged.connect(self._switch)
        self.nav.setCurrentRow(0)
        self.ctx.start_server()
        self.ctx.poll()

    def _switch(self, row: int) -> None:
        self.pages.setCurrentIndex(row)
        if row == 0:
            self.home.refresh()
        elif row == 3:
            self.cloud.refresh_charts()


def main() -> int:
    if sys.platform == "win32":
        # lets Windows show our icon on the taskbar instead of python.exe's
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Quasar.Windows.App")
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(QIcon(str(resource_path("quasar.ico"))))
    app.setStyleSheet(theme.QSS)
    window = MainWindow()
    window.show()
    return app.exec()
