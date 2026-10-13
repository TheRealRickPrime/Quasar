"""Compression Lab: compare size and speed of every format and level on real data."""
from __future__ import annotations

import csv
import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QGridLayout, QHBoxLayout, QHeaderView,
                               QLineEdit, QProgressBar, QPushButton, QScrollArea, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from .. import compression
from ..config import app_dir
from .context import AppContext
from .widgets import BarChart, card, fmt_size, fmt_time, label, page_header, run_task, set_status

SAMPLES = [("First 16 MB (quick)", 16), ("First 64 MB", 64), ("First 256 MB", 256), ("Whole file", 0)]


class LabPage(QWidget):
    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.setObjectName("page")
        self.ctx = ctx
        self.results: list[compression.CompressionResult] = []
        self.task = None

        inner = QWidget()
        inner.setObjectName("page")
        root = QVBoxLayout(inner)
        root.addWidget(page_header(
            "Compression Lab",
            "Run every format on the same data and compare resulting size, compression speed and "
            "decompression speed."))

        pick = card()
        pl = QVBoxLayout(pick)
        row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Choose a file, for example a .ab backup")
        browse = QPushButton("Browse…")
        latest = QPushButton("Use latest backup")
        browse.clicked.connect(self._browse)
        latest.clicked.connect(self._latest)
        row.addWidget(self.path_edit, 1)
        row.addWidget(browse)
        row.addWidget(latest)
        pl.addLayout(row)

        opts = QHBoxLayout()
        self.sample = QComboBox()
        for text, mb in SAMPLES:
            self.sample.addItem(text, mb)
        self.decomp = QCheckBox("Also time decompression")
        self.decomp.setChecked(True)
        opts.addWidget(label("Sample"))
        opts.addWidget(self.sample)
        opts.addWidget(self.decomp)
        opts.addStretch()
        pl.addLayout(opts)

        grid = QGridLayout()
        grid.addWidget(label("<b>Format</b>"), 0, 0)
        self.boxes: dict[tuple[str, str], QCheckBox] = {}
        for c, lv in enumerate(compression.LEVEL_ORDER, 1):
            grid.addWidget(label(f"<b>{lv.capitalize()}</b>"), 0, c)
        for r, spec in enumerate(compression.METHODS.values(), 1):
            grid.addWidget(label(f"{spec.label}  <span style='color:#8A8F98'>{spec.note}</span>"), r, 0)
            for c, lv in enumerate(compression.LEVEL_ORDER, 1):
                if lv in spec.levels:
                    box = QCheckBox(f"L{spec.levels[lv]}")
                    box.setChecked(lv == "balanced")
                    self.boxes[(spec.key, lv)] = box
                    grid.addWidget(box, r, c)
        pl.addLayout(grid)
        grid.setColumnStretch(0, 4)
        for c in (1, 2, 3):
            grid.setColumnStretch(c, 1)

        run_row = QHBoxLayout()
        self.run_btn = QPushButton("Run comparison")
        self.run_btn.setObjectName("primary")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.export_btn = QPushButton("Export CSV")
        self.export_btn.setEnabled(False)
        self.run_btn.clicked.connect(self._run)
        self.cancel_btn.clicked.connect(lambda: self.task and self.task.cancel.set())
        self.export_btn.clicked.connect(self._export)
        self.use_btn = QPushButton("Use these settings")
        self.use_btn.setToolTip("Select a row in the results (or leave none for the smallest) and use that "
                                "format and level for backups and phone images")
        self.use_btn.setEnabled(False)
        self.use_btn.clicked.connect(self._use_settings)
        for b in (self.run_btn, self.cancel_btn, self.export_btn, self.use_btn):
            run_row.addWidget(b)
        run_row.addStretch()
        pl.addLayout(run_row)
        self.status = label("", "muted")
        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        pl.addWidget(self.status)
        pl.addWidget(self.bar)
        root.addWidget(pick)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Format", "Level", "Size", "Saved", "Compress", "Speed",
                                              "Decompress"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(190)
        root.addWidget(self.table)

        self.verdict = label("", "")
        root.addWidget(self.verdict)
        charts = card()
        cl = QVBoxLayout(charts)
        self.size_chart = BarChart("Compressed size (smaller is better)", True)
        self.speed_chart = BarChart("Compression speed, MB/s (higher is better)", False)
        self.time_chart = BarChart("Decompression time (lower is better)", True)
        for ch in (self.size_chart, self.speed_chart, self.time_chart):
            cl.addWidget(ch)
        root.addWidget(charts)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(inner)
        scroll.viewport().setAutoFillBackground(False)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose a file to compress", str(self.ctx.settings.backup_dir))
        if path:
            self.path_edit.setText(path)

    def _latest(self) -> None:
        files = sorted(self.ctx.settings.backup_dir.glob("*.ab"), key=os.path.getmtime, reverse=True)
        if files:
            self.path_edit.setText(str(files[0]))
        else:
            set_status(self.status, "No .ab backups found yet. Browse for any file instead.", "warn")

    def _selections(self) -> list[tuple[str, str]]:
        return [key for key, box in self.boxes.items() if box.isChecked()]

    def _run(self) -> None:
        src = Path(self.path_edit.text().strip())
        if not src.is_file():
            set_status(self.status, "Choose an existing file first.", "bad")
            return
        picks = self._selections()
        if not picks:
            set_status(self.status, "Tick at least one format and level.", "bad")
            return
        mb = self.sample.currentData()
        limit = mb * 1024 * 1024 if mb else None
        self.results = []
        self.table.setRowCount(0)
        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.export_btn.setEnabled(False)
        work_dir = app_dir() / "lab"
        measure = self.decomp.isChecked()

        def work(report, cancel):
            return compression.benchmark(
                src, work_dir, picks, limit, on_status=lambda text, f: report(f, text),
                cancel=cancel, measure_decompress=measure)

        self.task = run_task(work, on_progress=self._progress, on_done=self._done,
                             on_failed=self._failed)

    def _progress(self, fraction: float, text: str) -> None:
        self.bar.setValue(int(fraction * 1000))
        set_status(self.status, text, "")

    def _failed(self, message: str) -> None:
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        set_status(self.status, f"Comparison failed: {message}", "bad")

    def _done(self, results: list) -> None:
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.results = results
        self.bar.setValue(1000)
        for r in results:
            row = self.table.rowCount()
            self.table.insertRow(row)
            label_ = compression.METHODS[r.method].label
            if r.error:
                cells = [label_, r.level, "failed", "", r.error[:40], "", ""]
            else:
                cells = [label_, r.level, fmt_size(r.compressed_size), f"{r.saved_percent:.1f}%",
                         fmt_time(r.seconds), f"{r.speed_mbps:.1f} MB/s",
                         fmt_time(r.decompress_seconds) if r.decompress_seconds is not None else "-"]
            for c, text in enumerate(cells):
                self.table.setItem(row, c, QTableWidgetItem(text))
            if not r.error:
                self.ctx.history.add("compress", method=r.method, level=r.level, original=r.original_size,
                                     compressed=r.compressed_size, seconds=r.seconds, source="lab")
        good = [r for r in results if not r.error]
        if not good:
            set_status(self.status, "No results.", "warn")
            return
        names = lambda r: f"{compression.METHODS[r.method].label} {r.level}"  # noqa: E731
        self.size_chart.set_rows([(names(r), r.compressed_size, fmt_size(r.compressed_size)) for r in good])
        self.speed_chart.set_rows([(names(r), r.speed_mbps, f"{r.speed_mbps:.1f} MB/s") for r in good])
        timed = [r for r in good if r.decompress_seconds is not None]
        self.time_chart.set_rows([(names(r), r.decompress_seconds, fmt_time(r.decompress_seconds))
                                  for r in timed])
        smallest = min(good, key=lambda r: r.compressed_size)
        fastest = min(good, key=lambda r: r.seconds)
        balanced = max(good, key=lambda r: r.saved_percent / max(r.seconds, 0.01) ** 0.5)
        set_status(self.verdict,
                   f"🏆 <b>Smallest:</b> {names(smallest)} ({fmt_size(smallest.compressed_size)}, "
                   f"{smallest.saved_percent:.1f}% saved) &nbsp;·&nbsp; <b>Fastest:</b> {names(fastest)} "
                   f"({fmt_time(fastest.seconds)}) &nbsp;·&nbsp; <b>Best balance:</b> {names(balanced)}", "good")
        set_status(self.status, f"Done: {len(good)} runs on {fmt_size(good[0].original_size)} of data.", "good")
        self.export_btn.setEnabled(True)
        self.use_btn.setEnabled(True)

    def _use_settings(self) -> None:
        good = [r for r in self.results if not r.error]
        row = self.table.currentRow()
        pick = self.results[row] if 0 <= row < len(self.results) and not self.results[row].error else None
        pick = pick or min(good, key=lambda r: r.compressed_size)
        self.ctx.settings.set("compression_method", pick.method)
        self.ctx.settings.set("compression_level", pick.level)
        note = ""
        if pick.method == "7z":
            note = " (7-Zip applies to guided backups only; phone images will use Zstandard)"
        set_status(self.status, f"Saved: {compression.METHODS[pick.method].label} / {pick.level} will be "
                                f"pre-selected on the Backup and Full Phone Image pages{note}.", "good")

    def _export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export results", "quasar-compression.csv", "CSV (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["method", "level", "original_bytes", "compressed_bytes", "saved_percent",
                        "compress_seconds", "speed_mb_s", "decompress_seconds"])
            for r in self.results:
                if not r.error:
                    w.writerow([r.method, r.level, r.original_size, r.compressed_size,
                                f"{r.saved_percent:.2f}", f"{r.seconds:.3f}", f"{r.speed_mbps:.2f}",
                                "" if r.decompress_seconds is None else f"{r.decompress_seconds:.3f}"])
