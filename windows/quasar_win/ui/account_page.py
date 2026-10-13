"""Quasar account: sign in to the backend, view backup sessions and the profile link."""
from __future__ import annotations

from PySide6.QtWidgets import (QFormLayout, QHBoxLayout, QHeaderView, QLineEdit, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from .context import AppContext
from .widgets import card, label, page_header, run_task, set_status


class AccountPage(QWidget):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.setObjectName("page")
        self.ctx = ctx
        root = QVBoxLayout(self)
        root.addWidget(page_header("Quasar account",
                                   "Optional. Sign in to record backup sessions and get your profile link."))
        box = card()
        lay = QVBoxLayout(box)
        form = QFormLayout()
        self.url = QLineEdit(ctx.settings.get("api_base_url"))
        self.name = QLineEdit()
        self.email = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        form.addRow("Server", self.url)
        form.addRow("Full name (register)", self.name)
        form.addRow("Email", self.email)
        form.addRow("Password", self.password)
        lay.addLayout(form)
        row = QHBoxLayout()
        self.login_btn = QPushButton("Sign in")
        self.login_btn.setObjectName("primary")
        self.register_btn = QPushButton("Register")
        self.logout_btn = QPushButton("Sign out")
        self.login_btn.clicked.connect(self._login)
        self.register_btn.clicked.connect(self._register)
        self.logout_btn.clicked.connect(self._logout)
        for b in (self.login_btn, self.register_btn, self.logout_btn):
            row.addWidget(b)
        row.addStretch()
        lay.addLayout(row)
        self.status = label("Not signed in. Passwords are never saved.", "muted")
        self.link = label("")
        lay.addWidget(self.status)
        lay.addWidget(self.link)
        root.addWidget(box)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Device", "Provider", "Status", "Created"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        root.addWidget(label("Backup sessions", "h2"))
        root.addWidget(self.table, 1)
        self._sync()

    def _apply_url(self) -> None:
        url = self.url.text().strip()
        self.ctx.settings.set("api_base_url", url)
        self.ctx.api.base_url = url.rstrip("/")

    def _login(self) -> None:
        self._apply_url()
        api, email, pw = self.ctx.api, self.email.text().strip(), self.password.text()
        set_status(self.status, "Signing in…", "")
        run_task(lambda _r, _c: (api.login(email, pw), api.sessions(), _safe_link(api)),
                 on_done=self._signed_in, on_failed=lambda m: set_status(self.status, f"✖ {m}", "bad"))

    def _signed_in(self, payload) -> None:
        _user, sessions, link = payload
        self.password.clear()
        self._fill(sessions)
        self.link.setText(f"Profile link: <b>{link.get('link_url')}</b>" if link else "")
        self._sync()

    def _register(self) -> None:
        self._apply_url()
        api = self.ctx.api
        args = (self.email.text().strip(), self.password.text(), self.name.text().strip())
        set_status(self.status, "Registering…", "")
        run_task(lambda _r, _c: api.register(*args),
                 on_done=lambda _u: set_status(self.status, "✔ Registered. Now sign in.", "good"),
                 on_failed=lambda m: set_status(self.status, f"✖ {m}", "bad"))

    def _logout(self) -> None:
        self.ctx.api.logout()
        self.table.setRowCount(0)
        self.link.setText("")
        self._sync()

    def _sync(self) -> None:
        on = self.ctx.api.logged_in
        self.logout_btn.setEnabled(on)
        self.login_btn.setEnabled(not on)
        self.register_btn.setEnabled(not on)
        if on:
            user = self.ctx.api.user
            set_status(self.status, f"✔ Signed in as {user.get('full_name') or user.get('email', '')}", "good")

    def _fill(self, sessions: list) -> None:
        self.table.setRowCount(0)
        for s in sessions:
            r = self.table.rowCount()
            self.table.insertRow(r)
            for c, key in enumerate(("device_name", "provider", "backup_status", "created_at")):
                self.table.setItem(r, c, QTableWidgetItem(str(s.get(key, ""))))


def _safe_link(api) -> dict:
    try:
        return api.profile_link()
    except Exception:
        return {}
