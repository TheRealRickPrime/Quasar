"""Application-wide state shared by all pages."""
from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal

from ..adb import Adb, AdbError, Device
from ..api import QuasarApi
from ..config import Settings
from ..history import History
from ..licensing import Licensing
from .widgets import run_task


class AppContext(QObject):
    devices_changed = Signal(list)
    adb_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.settings = Settings()
        self.history = History()
        self.licensing = Licensing()
        self.adb = Adb()
        self.api = QuasarApi(self.settings.get("api_base_url"))
        self.devices: list[Device] = []
        self.selected_serial = ""
        self.device_error = ""
        self._polling = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.poll)
        self._timer.start(2500)

    def reload_adb(self) -> None:
        self.adb = Adb()
        self.adb_changed.emit()
        self.poll()

    @property
    def device(self) -> Device | None:
        ready = [d for d in self.devices if d.ready]
        chosen = next((d for d in ready if d.serial == self.selected_serial), None)
        return chosen or (ready[0] if ready else None)

    def poll(self) -> None:
        if self._polling or not self.adb.available:
            return
        self._polling = True
        adb = self.adb

        def work(_report, _cancel):
            return adb.devices()

        def done(devices):
            self._polling = False
            self.device_error = ""
            if [(d.serial, d.state) for d in devices] != [(d.serial, d.state) for d in self.devices]:
                self.devices = devices
                self.devices_changed.emit(devices)

        def failed(message):
            self._polling = False
            self.device_error = message
            if self.devices:
                self.devices = []
                self.devices_changed.emit([])

        run_task(work, on_done=done, on_failed=failed)

    def provider(self):
        """The cloud destination chosen on the Cloud page, or None if not configured."""
        from ..cloud import PROVIDERS, make_provider
        from ..config import load_secret
        key = self.settings.get("provider")
        if key not in PROVIDERS:
            return None
        cfg = dict(self.settings.get("provider_settings", {}).get(key, {}))
        for f in PROVIDERS[key].fields:
            if f.secret:
                cfg[f.key] = load_secret(f"{key}.{f.key}")
        return make_provider(key, cfg) if any(cfg.values()) else None

    def start_server(self) -> None:
        if not self.adb.available:
            return

        def work(_r, _c):
            try:
                self.adb.start_server()
            except AdbError:
                pass

        run_task(work, on_done=lambda _: self.poll())
