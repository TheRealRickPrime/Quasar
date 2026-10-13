"""Shared UI building blocks: background, cards, charts, background tasks."""
from __future__ import annotations

import random
import threading
import traceback
from typing import Callable

from PySide6.QtCore import QObject, QRectF, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget

from . import theme


def fmt_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} TB"


def fmt_time(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds * 1000:.0f} ms"
    if seconds < 60:
        return f"{seconds:.1f} s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s:02d}s" if m < 60 else f"{m // 60}h {m % 60:02d}m"


class SpaceBackground(QWidget):
    """Deep-space gradient with softly twinkling stars."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        rng = random.Random(42)
        self._stars = [(rng.random(), rng.random(), rng.choice((1, 1, 1.4, 2)), rng.random() * 6.28)
                       for _ in range(160)]
        self._phase = 0.0
        timer = QTimer(self)
        timer.timeout.connect(self._tick)
        timer.start(80)

    def _tick(self) -> None:
        self._phase += 0.06
        self.update()

    def paintEvent(self, _event) -> None:
        import math
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        base = QLinearGradient(0, 0, w, h)
        base.setColorAt(0, QColor("#0B1430"))
        base.setColorAt(1, QColor("#04060D"))
        p.fillRect(self.rect(), base)
        for cx, cy, r, color in ((0.85, 0.1, 0.55, QColor(140, 60, 255, 60)),
                                 (0.1, 0.95, 0.6, QColor(0, 190, 255, 45))):
            glow = QRadialGradient(w * cx, h * cy, max(w, h) * r)
            glow.setColorAt(0, color)
            glow.setColorAt(1, QColor(0, 0, 0, 0))
            p.fillRect(self.rect(), glow)
        p.setPen(Qt.NoPen)
        for x, y, size, phase in self._stars:
            alpha = int(120 + 110 * math.sin(self._phase + phase))
            p.setBrush(QColor(225, 238, 255, max(40, min(alpha, 255))))
            p.drawEllipse(QRectF(x * w, y * h, size, size))


def card() -> QFrame:
    frame = QFrame()
    frame.setObjectName("card")
    return frame


def label(text: str = "", name: str = "", wrap: bool = True) -> QLabel:
    lab = QLabel(text)
    if name:
        lab.setObjectName(name)
    lab.setWordWrap(wrap)
    lab.setTextFormat(Qt.RichText)
    return lab


def page_header(title: str, subtitle: str) -> QWidget:
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 6)
    lay.setSpacing(2)
    lay.addWidget(label(title, "title", wrap=False))
    lay.addWidget(label(subtitle, "subtitle"))
    return box


def set_status(lab: QLabel, text: str, kind: str = "") -> None:
    lab.setObjectName(kind)
    lab.setText(text)
    lab.style().unpolish(lab)
    lab.style().polish(lab)


class BarChart(QWidget):
    """Horizontal bar chart; the best bar glows."""

    def __init__(self, title: str, lower_is_better: bool = True) -> None:
        super().__init__()
        self.title = title
        self.lower_is_better = lower_is_better
        self.rows: list[tuple[str, float, str]] = []
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

    def set_rows(self, rows: list[tuple[str, float, str]]) -> None:
        self.rows = rows
        self.setMinimumHeight(46 + 26 * max(len(rows), 1))
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QColor(theme.PAPER))
        font = QFont("Segoe UI", 10)
        font.setBold(True)
        p.setFont(font)
        p.drawText(0, 18, self.title)
        p.setFont(QFont("Segoe UI", 9))
        if not self.rows:
            p.setPen(QColor(theme.SOFT))
            p.drawText(0, 48, "Run a comparison to see results")
            return
        label_w, value_w = 150, 90
        bar_x, bar_w = label_w + 8, max(self.width() - label_w - value_w - 24, 40)
        peak = max(v for _, v, _ in self.rows) or 1.0
        values = [v for _, v, _ in self.rows]
        best = min(values) if self.lower_is_better else max(values)
        for i, (name, value, text) in enumerate(self.rows):
            y = 30 + i * 26
            p.setPen(QColor(theme.STEEL))
            p.drawText(QRectF(0, y, label_w, 20), Qt.AlignVCenter | Qt.AlignLeft,
                       p.fontMetrics().elidedText(name, Qt.ElideRight, label_w))
            width = max(bar_w * value / peak, 3)
            grad = QLinearGradient(bar_x, 0, bar_x + width, 0)
            is_best = value == best
            grad.setColorAt(0, QColor(theme.CYAN))
            grad.setColorAt(1, QColor(theme.VIOLET if not is_best else theme.GOOD))
            if is_best:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(61, 220, 151, 50))
                p.drawRoundedRect(QRectF(bar_x - 2, y - 2, width + 4, 22), 7, 7)
            p.setPen(Qt.NoPen)
            p.setBrush(grad)
            p.drawRoundedRect(QRectF(bar_x, y, width, 18), 5, 5)
            p.setPen(QColor(theme.GOOD if is_best else theme.PAPER))
            p.drawText(QRectF(bar_x + width + 8, y, value_w, 18), Qt.AlignVCenter, text)


class _Signals(QObject):
    progress = Signal(float, str)
    done = Signal(object)
    failed = Signal(str)


class Task(QRunnable):
    """Run fn(report, cancel) on the thread pool; results arrive via Qt signals."""

    def __init__(self, fn: Callable[[Callable[[float, str], None], threading.Event], object]) -> None:
        super().__init__()
        self.fn = fn
        self.cancel = threading.Event()
        self.signals = _Signals()
        self.setAutoDelete(False)

    def run(self) -> None:
        try:
            result = self.fn(self.signals.progress.emit, self.cancel)
        except Exception as exc:
            traceback.print_exc()
            self.signals.failed.emit(str(exc) or exc.__class__.__name__)
        else:
            self.signals.done.emit(result)


_ACTIVE: set[Task] = set()


def run_task(fn, on_progress=None, on_done=None, on_failed=None) -> Task:
    task = Task(fn)
    _ACTIVE.add(task)
    task.signals.done.connect(lambda _r: _ACTIVE.discard(task))
    task.signals.failed.connect(lambda _m: _ACTIVE.discard(task))
    if on_progress:
        task.signals.progress.connect(on_progress)
    if on_done:
        task.signals.done.connect(on_done)
    if on_failed:
        task.signals.failed.connect(on_failed)
    QThreadPool.globalInstance().start(task)
    return task
