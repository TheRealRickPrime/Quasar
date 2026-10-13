"""Post-backup pipeline: compress -> encrypt (+verify) -> upload, with timings per stage."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import compression, encryption
from .cloud import Provider, UploadError
from .history import History

Report = Callable[[float, str], None]


@dataclass
class Stage:
    name: str
    input_size: int
    output_size: int
    seconds: float
    detail: str = ""


@dataclass
class PipelineResult:
    final_path: Path
    stages: list[Stage] = field(default_factory=list)
    upload_location: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass
class PipelineOptions:
    compression: str = ""          # "" = none
    level: str = "balanced"
    passphrase: str = ""           # "" = no encryption
    security: str = "enhanced"
    delete_original: bool = True
    provider: Provider | None = None


def run_pipeline(raw: Path, opts: PipelineOptions, report: Report, cancel: threading.Event,
                 history: History | None = None) -> PipelineResult:
    current = raw
    result = PipelineResult(raw)
    stages_total = sum([bool(opts.compression), bool(opts.passphrase), opts.provider is not None])
    index = 0

    def stage_report(text: str):
        def inner(fraction: float) -> None:
            report((index + fraction) / max(stages_total, 1), text)
        return inner

    intermediates: list[Path] = []

    if opts.compression:
        spec = compression.METHODS[opts.compression]
        out = raw.with_name(compression.output_name(raw, opts.compression))
        r = compression.compress(current, out, opts.compression, opts.level,
                                 stage_report(f"Compressing ({spec.label})"), cancel)
        result.stages.append(Stage(f"Compress - {spec.label} ({r.level})", r.original_size,
                                   r.compressed_size, r.seconds,
                                   f"{r.saved_percent:.1f}% saved, {r.speed_mbps:.1f} MB/s"))
        if history:
            history.add("compress", method=opts.compression, level=r.level, original=r.original_size,
                        compressed=r.compressed_size, seconds=r.seconds, source="backup")
        if r.compressed_size >= r.original_size:
            result.warnings.append("Compression did not shrink the file; adb backups are already "
                                   "deflated. Consider 'None' for faster uploads.")
        current = out
        index += 1

    if opts.passphrase:
        out = current.with_name(current.name + ".qsr")
        size_in = current.stat().st_size
        t0 = time.perf_counter()
        encryption.encrypt_file(current, out, opts.passphrase, opts.security,
                                stage_report("Encrypting"), cancel)
        encryption.verify_file(out, opts.passphrase, stage_report("Verifying encrypted file"))
        result.stages.append(Stage(f"Encrypt - {encryption.SECURITY_LEVELS[opts.security]}",
                                   size_in, out.stat().st_size, time.perf_counter() - t0,
                                   "verified: every block authenticates"))
        if current != raw:
            intermediates.append(current)
        current = out
        index += 1
        if opts.delete_original:
            intermediates.append(raw)

    for path in intermediates:
        path.unlink(missing_ok=True)
    if opts.passphrase and opts.delete_original:
        result.warnings.append("Unencrypted original removed after the encrypted copy was verified.")
    result.final_path = current

    if opts.provider is not None:
        size = current.stat().st_size
        base = index

        def up(sent: int, total: int) -> None:
            report((base + (sent / total if total else 1)) / max(stages_total, 1),
                   f"Uploading to {opts.provider.label}")

        try:
            res = opts.provider.upload(current, up, cancel)
        except UploadError:
            raise
        result.stages.append(Stage(f"Upload - {opts.provider.label}", size, size, res.seconds,
                                   f"{res.speed_mbps:.1f} Mbit/s ({res.speed_mb_s:.2f} MB/s)"))
        result.upload_location = res.location
        if history:
            history.add("upload", provider=opts.provider.key, size=size, seconds=res.seconds,
                        speed_mbps=res.speed_mbps, test=False)
    report(1.0, "Done")
    return result
