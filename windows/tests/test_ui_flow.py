import os
import time
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

from PySide6.QtWidgets import QApplication  # noqa: E402

FAKE_ADB = r"""@echo off
if "%1"=="start-server" exit /b 0
if "%1"=="devices" (
  echo List of devices attached
  echo FAKE123 device usb:1-1 model:Pixel_7 transport_id:1
  exit /b 0
)
if "%3"=="shell" (
  if "%5"=="ro.build.version.sdk" (echo 33) else if "%5"=="ro.build.version.release" (echo 13) else echo Pixel 7
  exit /b 0
)
if "%3"=="backup" (
  (echo ANDROID BACKUP& echo 5& echo 1& echo none) > "%5"
  fsutil file createnew "%5.pad" 200000 >nul
  type "%5.pad" >> "%5"
  del "%5.pad"
  exit /b 0
)
exit /b 1
"""


def wait_until(app, condition, timeout=60):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.05)
    return False


@pytest.fixture()
def window(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    app = QApplication.instance() or QApplication([])
    from quasar_win.adb import Adb
    from quasar_win.ui.main_window import MainWindow
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)

    fake = tmp_path / "adb.bat"
    fake.write_text(FAKE_ADB)
    win = MainWindow()
    win.ctx.settings.set("backup_dir", str(tmp_path / "backups"))
    win.ctx.settings.set("provider", "local_folder")
    win.ctx.settings.set("provider_settings", {"local_folder": {"path": str(tmp_path / "cloud")}})
    win.ctx.adb = Adb(fake)
    yield app, win, tmp_path
    win.close()


def test_wizard_end_to_end(window):
    app, win, tmp_path = window
    wizard = win.pages.widget(1)
    win.ctx.poll()
    assert wait_until(app, lambda: win.ctx.device is not None)
    assert win.ctx.device.title == "Pixel 7" and win.ctx.device.sdk == 33

    wizard.go(0)
    assert wizard.next_btn.isEnabled()
    wizard.go(1)
    assert not wizard.next_btn.isEnabled()
    for box in wizard.checks:
        box.setChecked(True)
    assert wizard.next_btn.isEnabled()

    wizard.go(2)
    assert "Pixel 7" in wizard.conn_title.text() and wizard.next_btn.isEnabled()

    wizard.go(3)
    wizard.comp_method.setCurrentIndex(wizard.comp_method.findData("zstd"))
    wizard.pass1.setText("short")
    assert not wizard.next_btn.isEnabled()  # passphrase too short
    wizard.pass1.setText("correct horse battery")
    wizard.pass2.setText("different")
    assert not wizard.next_btn.isEnabled()
    wizard.pass2.setText("correct horse battery")
    assert wizard.next_btn.isEnabled()
    assert wizard.upload_check.isEnabled()
    wizard.upload_check.setChecked(True)

    wizard.go(4)
    assert not wizard.next_btn.isEnabled()
    wizard.bk_start.click()
    assert wait_until(app, lambda: wizard.backup_ok), wizard.bk_status.text()
    assert wizard.raw_path.exists() and wizard.next_btn.isEnabled()

    wizard.go(5)
    wizard.pl_start.click()
    assert wait_until(app, lambda: wizard.pl_table.rowCount() == 3), wizard.pl_status.text()
    names = [wizard.pl_table.item(r, 0).text() for r in range(3)]
    assert names[0].startswith("Compress") and names[1].startswith("Encrypt") and names[2].startswith("Upload")
    cloud = list((tmp_path / "cloud").iterdir())
    assert len(cloud) == 1 and cloud[0].name.endswith(".ab.zst.qsr")
    assert not list((tmp_path / "backups").glob("*.ab"))  # raw original removed
    assert [r["kind"] for r in win.ctx.history.all()] == ["compress", "upload"]


def test_empty_backup_is_reported(window):
    app, win, tmp_path = window
    from quasar_win.adb import Adb
    empty = tmp_path / "adb_empty.bat"
    empty.write_text(FAKE_ADB.replace('fsutil file createnew "%5.pad" 200000 >nul',
                                      'echo. > "%5.pad"').replace("type", "rem"))
    win.ctx.adb = Adb(empty)
    wizard = win.pages.widget(1)
    win.ctx.poll()
    assert wait_until(app, lambda: win.ctx.device is not None)
    wizard.go(4)
    wizard.bk_start.click()
    assert wait_until(app, lambda: not wizard._backup_running)
    assert not wizard.backup_ok and "no data" in wizard.bk_status.text()


def test_lab_runs_and_fills_charts(window):
    app, win, tmp_path = window
    lab = win.pages.widget(2)
    src = tmp_path / "x.bin"
    src.write_bytes(b"quasar " * 100_000 + os.urandom(100_000))
    lab.path_edit.setText(str(src))
    for key, box in lab.boxes.items():
        box.setChecked(key in {("zstd", "fast"), ("tar.gz", "balanced")})
    lab.run_btn.click()
    assert wait_until(app, lambda: lab.table.rowCount() == 2), lab.status.text()
    assert len(lab.size_chart.rows) == 2 and "Smallest" in lab.verdict.text()
    assert lab.export_btn.isEnabled()


def test_cloud_speed_test_records_history(window):
    app, win, tmp_path = window
    cloud = win.pages.widget(3)
    cloud.provider.setCurrentIndex(cloud.provider.findData("local_folder"))
    cloud.inputs["path"].setText(str(tmp_path / "speedcloud"))
    cloud.test_size.setCurrentIndex(0)
    cloud.speed_btn.click()
    assert wait_until(app, lambda: cloud.upload_btn.isEnabled() and win.ctx.history.of_kind("upload"))
    assert cloud.speed_chart.rows and "Mbit/s" in cloud.speed_chart.rows[0][2]
