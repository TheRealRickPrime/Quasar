import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

from PySide6.QtWidgets import QApplication  # noqa: E402

from quasar_win.adb import Device  # noqa: E402
from test_image import RestoringAdb  # noqa: E402
from test_ui_flow import wait_until, window  # noqa: E402,F401


def test_free_limit_blocks_backup_start(window):
    app, win, tmp = window
    win.ctx.devices = [Device("S1", "device", model="Pixel_7")]
    for _ in range(15):
        win.ctx.licensing.record_backup()
    wizard = win.pages.widget(1)
    wizard._start_backup()
    assert "15 backups" in wizard.bk_status.text()
    assert not getattr(wizard, "_backup_running", False)
    page = win.pages.widget(7)
    page.refresh()
    assert "Free" in page.plan_label.text() and "15 of 15" in page.backup_text.text()


def test_image_page_create_and_restore(window):
    app, win, tmp = window
    adb = RestoringAdb()
    win.ctx.adb = adb
    win.ctx.devices = [Device("S1", "device", model="Pixel_7")]
    page = win.pages.widget(6)
    page._refresh()

    page._detect()
    assert wait_until(app, lambda: page.access is not None and page.parts)
    assert page.access.kind == "adb-root"
    assert page.table.rowCount() == 3
    assert page._chosen() and all(p.name != "xbl" for p in page._chosen())

    page.dest.setText(str(tmp / "images"))
    from PySide6.QtWidgets import QMessageBox
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
    page._start_image()
    assert wait_until(app, lambda: not page.busy and "Image complete" in page.log.toPlainText())

    folder = next((tmp / "images").iterdir())
    page.src.setText(str(folder))
    page.manifest = __import__("quasar_win.image", fromlist=["x"]).load_manifest(folder)
    page._pick_image = lambda: None
    page.rtable.setRowCount(len(page.manifest["partitions"]))
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QTableWidgetItem
    for i, r in enumerate(page.manifest["partitions"]):
        chk = QTableWidgetItem()
        chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        chk.setCheckState(Qt.Checked)
        page.rtable.setItem(i, 0, chk)

    page._verify()
    assert wait_until(app, lambda: "match their checksums" in page.log.toPlainText())

    page.confirm.setText("RESTORE")
    assert page.restore_btn.isEnabled()
    page._start_restore()
    assert wait_until(app, lambda: "recovery" in page.log.toPlainText().lower() and not page.busy)
    assert "Failed" in page.log.toPlainText()  # live system must not restore userdata

    from quasar_win.image import Access
    page.access = Access("recovery", False)
    original = adb.disk["/dev/block/sda1"]
    adb.disk["/dev/block/sda1"] = b"broken"
    page._start_restore()
    assert wait_until(app, lambda: "read-back verified" in page.log.toPlainText())
    assert adb.disk["/dev/block/sda1"] == original
