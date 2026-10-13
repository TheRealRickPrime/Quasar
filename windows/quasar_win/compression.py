"""Compression engine with the same formats as the Android app.

Every method streams file-to-file, reports progress and can be cancelled, so the
same code drives the real backup pipeline and the benchmark lab.
"""
from __future__ import annotations

import bz2
import io
import lzma
import tarfile
import threading
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import py7zr
import zstandard

Progress = Callable[[float], None]
CHUNK = 1024 * 1024


class Cancelled(Exception):
    pass


@dataclass(frozen=True)
class Method:
    key: str
    label: str
    extension: str
    levels: dict[str, int]
    note: str


# fast / balanced / max map to the closest native level of each codec
METHODS: dict[str, Method] = {
    "zstd": Method("zstd", "Zstandard", ".zst", {"fast": 3, "balanced": 12, "max": 19},
                   "Best ratio-to-speed; Android default"),
    "zstd-ultra": Method("zstd-ultra", "Zstandard Ultra", ".zst", {"max": 22},
                         "Level 22, slowest and smallest"),
    "tar.gz": Method("tar.gz", "TAR + Gzip", ".tar.gz", {"fast": 1, "balanced": 6, "max": 9},
                     "Universal compatibility"),
    "tar.bz2": Method("tar.bz2", "TAR + Bzip2", ".tar.bz2", {"fast": 1, "balanced": 5, "max": 9},
                      "Good ratio, slow"),
    "tar.xz": Method("tar.xz", "TAR + XZ", ".tar.xz", {"fast": 1, "balanced": 6, "max": 9},
                     "Very small, very slow"),
    "zip": Method("zip", "ZIP (Deflate)", ".zip", {"fast": 1, "balanced": 6, "max": 9},
                  "Opens everywhere on Windows"),
    "7z": Method("7z", "7-Zip (LZMA2)", ".7z", {"fast": 1, "balanced": 5, "max": 9},
                 "Strong ratio, needs 7-Zip to open"),
}
LEVEL_ORDER = ("fast", "balanced", "max")


@dataclass
class CompressionResult:
    method: str
    level: str
    source: str
    output: str
    original_size: int
    compressed_size: int
    seconds: float
    decompress_seconds: float | None = None
    error: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def ratio(self) -> float:
        return self.compressed_size / self.original_size if self.original_size else 1.0

    @property
    def saved_percent(self) -> float:
        return (1.0 - self.ratio) * 100.0

    @property
    def speed_mbps(self) -> float:
        return (self.original_size / 1_048_576) / self.seconds if self.seconds > 0 else 0.0


class _ProgressReader(io.RawIOBase):
    """File wrapper that reports read progress and honours cancellation."""

    def __init__(self, path: Path, progress: Progress | None, cancel: threading.Event | None,
                 limit: int | None = None) -> None:
        self._f = open(path, "rb")
        self._size = min(path.stat().st_size, limit) if limit else path.stat().st_size
        self._read = 0
        self._progress = progress
        self._cancel = cancel

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._read

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self._read, io.SEEK_END: self._size}[whence]
        self._read = max(0, min(base + offset, self._size))
        self._f.seek(self._read)
        return self._read

    def readinto(self, buffer) -> int:  # type: ignore[override]
        if self._cancel and self._cancel.is_set():
            raise Cancelled()
        remaining = self._size - self._read
        if remaining <= 0:
            return 0
        view = memoryview(buffer)[: min(len(buffer), remaining)]
        n = self._f.readinto(view)
        self._read += n
        if self._progress and self._size:
            self._progress(self._read / self._size)
        return n

    @property
    def size(self) -> int:
        return self._size

    def close(self) -> None:
        self._f.close()
        super().close()


def _tar_member(name: str, size: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size = size
    info.mtime = int(time.time())
    info.mode = 0o644
    return info


def _compress(src: Path, dst: Path, method: str, level: int, progress: Progress | None,
              cancel: threading.Event | None, limit: int | None) -> None:
    reader = _ProgressReader(src, progress, cancel, limit)
    name = src.name
    try:
        if method in ("zstd", "zstd-ultra"):
            params = zstandard.ZstdCompressionParameters.from_level(
                level, threads=-1, enable_ldm=level >= 19, window_log=27 if level >= 19 else 0)
            with open(dst, "wb") as out, zstandard.ZstdCompressor(compression_params=params) \
                    .stream_writer(out, size=reader.size) as writer:
                while chunk := reader.read(CHUNK):
                    writer.write(chunk)
        elif method == "zip":
            with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=level) as zf:
                with zf.open(name, "w", force_zip64=True) as member:
                    while chunk := reader.read(CHUNK):
                        member.write(chunk)
        elif method == "7z":
            filters = [{"id": py7zr.FILTER_LZMA2, "preset": level}]
            with py7zr.SevenZipFile(dst, "w", filters=filters) as archive:
                archive.writef(io.BufferedReader(reader), name)
        elif method in ("tar.gz", "tar.bz2", "tar.xz"):
            mode = {"tar.gz": "w:gz", "tar.bz2": "w:bz2", "tar.xz": "w:xz"}[method]
            kwargs = {"preset": level} if method == "tar.xz" else {"compresslevel": level}
            with tarfile.open(dst, mode, **kwargs) as tar:
                tar.addfile(_tar_member(name, reader.size), io.BufferedReader(reader))
        else:
            raise ValueError(f"Unknown compression method: {method}")
    finally:
        reader.close()


def output_name(src: Path, method: str) -> str:
    return src.name + METHODS[method].extension


def compress(src: Path, dst: Path, method: str, level_name: str = "balanced",
             progress: Progress | None = None, cancel: threading.Event | None = None,
             limit: int | None = None) -> CompressionResult:
    spec = METHODS[method]
    if level_name not in spec.levels:
        level_name = list(spec.levels)[-1]
    original = min(src.stat().st_size, limit) if limit else src.stat().st_size
    start = time.perf_counter()
    try:
        _compress(src, dst, method, spec.levels[level_name], progress, cancel, limit)
    except BaseException:
        dst.unlink(missing_ok=True)
        raise
    elapsed = time.perf_counter() - start
    return CompressionResult(method, level_name, str(src), str(dst), original,
                             dst.stat().st_size, elapsed)


def decompress(src: Path, out_dir: Path) -> Path:
    """Extract a single-file archive produced by compress() and return its path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    name = src.name
    if name.endswith(".zst"):
        target = out_dir / name[: -len(".zst")]
        with open(src, "rb") as fin, open(target, "wb") as fout:
            zstandard.ZstdDecompressor().copy_stream(fin, fout, CHUNK, CHUNK)
        return target
    if name.endswith(".zip"):
        with zipfile.ZipFile(src) as zf:
            member = zf.namelist()[0]
            zf.extract(member, out_dir)
            return out_dir / member
    if name.endswith(".7z"):
        with py7zr.SevenZipFile(src) as archive:
            member = archive.getnames()[0]
            archive.extract(out_dir)
            return out_dir / member
    if name.endswith((".tar.gz", ".tar.bz2", ".tar.xz")):
        with tarfile.open(src) as tar:
            member = tar.getmembers()[0]
            tar.extract(member, out_dir, filter="data")
            return out_dir / member.name
    raise ValueError(f"Unrecognised archive: {name}")


def benchmark(src: Path, work_dir: Path, selections: list[tuple[str, str]],
              sample_bytes: int | None = None,
              on_result: Callable[[CompressionResult], None] | None = None,
              on_status: Callable[[str, float], None] | None = None,
              cancel: threading.Event | None = None,
              measure_decompress: bool = True) -> list[CompressionResult]:
    """Run each (method, level) against the same input and compare size and speed."""
    work_dir.mkdir(parents=True, exist_ok=True)
    results: list[CompressionResult] = []
    total = len(selections)
    for index, (method, level) in enumerate(selections):
        if cancel and cancel.is_set():
            break
        label = f"{METHODS[method].label} ({level})"

        def step(fraction: float, i=index, text=label) -> None:
            if on_status:
                on_status(f"Compressing with {text}", (i + fraction) / total)

        out = work_dir / output_name(src, method)
        try:
            result = compress(src, out, method, level, step, cancel, sample_bytes)
            if measure_decompress:
                t0 = time.perf_counter()
                restored = decompress(out, work_dir / "restore")
                result.decompress_seconds = time.perf_counter() - t0
                restored.unlink(missing_ok=True)
        except Cancelled:
            break
        except Exception as exc:  # keep going so one broken codec doesn't kill the run
            result = CompressionResult(method, level, str(src), str(out), 0, 0, 0.0, error=str(exc))
        finally:
            Path(out).unlink(missing_ok=True)
        results.append(result)
        if on_result:
            on_result(result)
    return results
