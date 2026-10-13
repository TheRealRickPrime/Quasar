"""Render every page headlessly to PNGs (used for visual checks).

Run: python tools/screenshots.py <output_dir>
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="quasar-shots-")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

from quasar_win.ui import theme  # noqa: E402
from quasar_win.ui.main_window import MainWindow  # noqa: E402


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    app.setStyleSheet(theme.QSS)
    win = MainWindow()
    win.show()
    app.processEvents()
    wizard = win.pages.widget(1)
    for row, name in enumerate(["home", "backup", "lab", "cloud", "account", "app", "image"]):
        win.nav.setCurrentRow(row)
        if name == "backup":
            for step in range(6):
                for box in wizard.checks:
                    box.setChecked(True)
                wizard.go(step)
                app.processEvents()
                win.grab().save(str(out / f"backup-{step + 1}.png"))
            wizard.go(0)
        app.processEvents()
        win.grab().save(str(out / f"{name}.png"))
    print("saved to", out)


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "shots"))
