"""Full partition imaging and restore (raw block devices over ADB).

Two ways to get root-level access to the phone's partitions:
  * recovery  - a custom recovery (TWRP etc.) is running; adbd is root and nothing is mounted,
                so the data is naturally consistent.
  * magisk    - the phone is booted normally and `su` is granted. Live partitions change
                underneath us, so the framework is paused and /data is remounted read-only
                while imaging (see `Quiesce`).
"""
from __future__ import annotations

import bz2
import gzip
import hashlib
import json
import lzma
import os
import re
import shlex
import shutil
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

import zipfile

import zstandard

from . import __version__, compression
from .adb import Adb, AdbError

CHUNK = 1024 * 1024
MANIFEST = "quasar-image.json"
Progress = Callable[[str, int, int, float], None]  # partition, done, total, bytes/sec

BOOTCHAIN = {"xbl", "xbl_config", "xbl_ac", "abl", "aboot", "sbl1", "sbl2", "sbl3", "tz", "rpm", "hyp",
             "pmic", "devcfg", "keymaster", "cmnlib", "cmnlib64", "qupfw", "uefisecapp", "bootloader",
             "preloader", "lk", "tee", "prog_firehose", "storsec", "imagefv", "shrm", "aop", "multiimgoem"}
DATA = {"userdata", "metadata", "persist"}
RADIO = {"modem", "modemst1", "modemst2", "fsg", "fsc", "efs", "bluetooth", "dsp", "nvdata", "nvram",
         "nvcfg", "protect1", "protect2", "radio", "apnhlos", "mdm1m9kefs1", "mdm1m9kefs2"}
CORE = {"boot", "init_boot", "vendor_boot", "recovery", "dtbo", "vbmeta", "vbmeta_system", "vbmeta_vendor",
        "system", "system_ext", "vendor", "product", "odm", "super", "vendor_dlkm", "odm_dlkm",
        "system_dlkm", "vm-bootsys"}
SKIP_DEFAULT = {"cache", "userdata_ext", "ddr", "sda", "sdb", "sdc", "sdd", "sde", "sdf"}
# restoring these can permanently brick a device, so they need an explicit override
RESTORE_LIVE_SAFE = {"boot", "init_boot", "vendor_boot", "recovery", "dtbo", "vbmeta", "vbmeta_system",
                     "vbmeta_vendor"}


class ImageError(Exception):
    pass


def base_name(name: str) -> str:
    return re.sub(r"_(a|b)$", "", name)


def classify(name: str) -> str:
    base = base_name(name)
    if base in BOOTCHAIN:
        return "bootchain"
    if base in DATA:
        return "data"
    if base in RADIO or base.startswith(("modem", "fsg", "efs")):
        return "radio"
    if base in CORE:
        return "core"
    return "other"


@dataclass
class Partition:
    name: str
    dev: str
    size: int
    kind: str = ""
    selected: bool = True

    def __post_init__(self) -> None:
        self.kind = self.kind or classify(self.name)
        self.selected = self.kind != "bootchain" and base_name(self.name) not in SKIP_DEFAULT and self.size > 0


@dataclass
class PartitionRecord:
    name: str
    dev: str
    size: int
    kind: str
    file: str
    sha256: str
    stored_size: int
    compression: str
    seconds: float


@dataclass
class Access:
    kind: str  # recovery | adb-root | magisk
    use_su: bool

    @property
    def live(self) -> bool:
        return self.kind != "recovery"

    @property
    def label(self) -> str:
        return {"recovery": "Custom recovery (adb root)", "adb-root": "adb root (live system)",
                "magisk": "Magisk / su (live system)"}[self.kind]

    def wrap(self, command: str) -> str:
        return f"su -c {shlex.quote(command)}" if self.use_su else command


def detect_access(adb: Adb, serial: str, su_timeout: float = 45) -> Access:
    rc, out = adb.shell(serial, "id -u")
    if rc == 0 and out.strip() == "0":
        _, twrp = adb.shell(serial, "getprop ro.twrp.version; getprop init.svc.recovery; getprop ro.bootmode")
        return Access("recovery" if re.search(r"\d|running|recovery", twrp) else "adb-root", False)
    try:
        rc, out = adb.shell(serial, "su -c id -u", timeout=su_timeout)
    except AdbError:
        rc, out = 1, ""
    if rc == 0 and out.strip().endswith("0"):
        return Access("magisk", True)
    raise ImageError(
        "No root access. Either boot a custom recovery (adb is root there), or install Magisk "
        "and approve the 'Shell' superuser request on the phone, then try again.")


def device_info(adb: Adb, serial: str) -> dict:
    wanted = {"model": "ro.product.model", "device": "ro.product.device", "brand": "ro.product.brand",
              "android": "ro.build.version.release", "build": "ro.build.fingerprint",
              "slot": "ro.boot.slot_suffix", "serial": "ro.serialno"}
    info = {}
    for key, prop in wanted.items():
        try:
            info[key] = adb.shell(serial, f"getprop {prop}", timeout=10)[1].strip()
        except AdbError:
            info[key] = ""
    return info


_LIST_CMD = (
    "d=$(ls -d /dev/block/by-name /dev/block/bootdevice/by-name /dev/block/platform/*/by-name "
    "/dev/block/platform/*/*/by-name 2>/dev/null | head -n 1); "
    "for f in $d/*; do n=${f##*/}; echo \"$n|$(readlink -f $f)|$(blockdev --getsize64 $f)\"; done"
)


def parse_partitions(output: str) -> list[Partition]:
    parts = []
    for line in output.splitlines():
        bits = line.strip().split("|")
        if len(bits) == 3 and bits[2].isdigit() and bits[1].startswith("/dev/"):
            parts.append(Partition(bits[0], bits[1], int(bits[2])))
    return sorted(parts, key=lambda p: p.name)


def list_partitions(adb: Adb, serial: str, access: Access) -> list[Partition]:
    rc, out = adb.shell(serial, access.wrap(_LIST_CMD), timeout=60)
    parts = parse_partitions(out)
    if not parts:
        raise ImageError("Could not find the partition table (/dev/block/by-name). "
                         "This phone may not expose named partitions to root.")
    return parts


class Quiesce:
    """Make a live system's partitions stable while we read them.

    Stops the Android framework so apps stop writing, syncs, then tries to remount /data
    read-only. Always undone on exit. It is not a copy-on-write snapshot: Android has no
    generic one for userdata, so if the remount is refused the image is crash-consistent
    only (like pulling the power), which f2fs/ext4 journals recover from.
    """

    def __init__(self, adb: Adb, serial: str, access: Access, log: Callable[[str], None] = lambda m: None):
        self.adb, self.serial, self.access, self.log = adb, serial, access, log
        self.framework_stopped = False
        self.data_readonly = False
        self._data_was_rw = False

    def _sh(self, cmd: str, timeout: float = 60) -> tuple[int, str]:
        return self.adb.shell(self.serial, self.access.wrap(cmd), timeout=timeout)

    def __enter__(self) -> "Quiesce":
        if not self.access.live:
            return self
        self.log("Pausing Android so data stops changing (the phone screen will freeze)…")
        self.framework_stopped = self._sh("stop")[0] == 0
        time.sleep(1.5)
        self._sh("sync")
        _, mounts = self._sh("grep ' /data ' /proc/mounts")
        self._data_was_rw = bool(re.search(r"[ ,]rw[ ,]", mounts))
        if self._data_was_rw:
            self._sh("mount -o remount,ro /data")
            _, mounts = self._sh("grep ' /data ' /proc/mounts")
        self.data_readonly = bool(mounts) and not re.search(r"[ ,]rw[ ,]", mounts)
        self.log("/data is read-only: consistent image." if self.data_readonly else
                 "/data could not be made read-only: image will be crash-consistent.")
        return self

    def __exit__(self, *exc) -> None:
        if not self.access.live:
            return
        try:
            if self._data_was_rw and self.data_readonly:
                self._sh("mount -o remount,rw /data")
            if self.framework_stopped:
                self._sh("start")
                self.log("Android resumed.")
        except AdbError:
            self.log("Could not resume Android automatically. Reboot the phone.")


# Lab method key -> (codec name stored in the manifest, file suffix). Only formats that can be
# written as a single stream are offered for images (7z and tar need a seekable archive).
IMAGE_METHODS = {"zstd": ("zstd", ".zst"), "zstd-ultra": ("zstd", ".zst"), "tar.gz": ("gzip", ".gz"),
                 "tar.bz2": ("bzip2", ".bz2"), "tar.xz": ("xz", ".xz"), "zip": ("zip", ".zip")}


class _ZipStream:
    def __init__(self, raw, level: int):
        self.zf = zipfile.ZipFile(raw, "w", zipfile.ZIP_DEFLATED, compresslevel=level)
        self.member = self.zf.open("image", "w", force_zip64=True)

    def write(self, data: bytes) -> int:
        return self.member.write(data)

    def close(self) -> None:
        self.member.close()
        self.zf.close()


def _open_out(path: Path, compress: bool, method: str, level_name: str):
    raw = open(path, "wb")
    if not compress:
        return raw, raw
    spec = compression.METHODS[method]
    level = spec.levels.get(level_name) or list(spec.levels.values())[-1]
    codec = IMAGE_METHODS[method][0]
    if codec == "zstd":
        return zstandard.ZstdCompressor(level=level, threads=-1).stream_writer(raw, closefd=False), raw
    if codec == "gzip":
        return gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=level), raw
    if codec == "bzip2":
        return bz2.BZ2File(raw, "wb", compresslevel=level), raw
    if codec == "xz":
        return lzma.LZMAFile(raw, "wb", preset=level), raw
    return _ZipStream(raw, level), raw


def image_partition(adb: Adb, serial: str, access: Access, part: Partition, out_dir: Path,
                    compress: bool = True, method: str = "zstd", level_name: str = "fast",
                    on_progress: Progress | None = None,
                    cancel: threading.Event | None = None) -> PartitionRecord:
    out_dir.mkdir(parents=True, exist_ok=True)
    if compress and method not in IMAGE_METHODS:
        raise ImageError(f"{method} can't be used for phone images; pick Zstandard, Gzip, Bzip2, XZ or ZIP.")
    codec, ext = IMAGE_METHODS[method] if compress else ("none", "")
    suffix = ".img" + ext
    final, temp = out_dir / f"{part.name}{suffix}", out_dir / f"{part.name}{suffix}.part"
    command = access.wrap(f"dd if={part.dev} bs={CHUNK} 2>/dev/null")
    sha, total, start = hashlib.sha256(), 0, time.perf_counter()
    proc = adb.popen_out(serial, command)
    writer, raw = _open_out(temp, compress, method, level_name)
    try:
        while True:
            if cancel and cancel.is_set():
                raise ImageError("Cancelled")
            chunk = proc.stdout.read(CHUNK)
            if not chunk:
                break
            sha.update(chunk)
            writer.write(chunk)
            total += len(chunk)
            if on_progress:
                on_progress(part.name, total, part.size, total / max(time.perf_counter() - start, 1e-6))
        if compress:
            writer.close()
        raw.close()
        proc.wait(timeout=30)
        if total != part.size:
            raise ImageError(f"{part.name}: received {total} of {part.size} bytes (transfer was cut short)")
        temp.replace(final)
    except BaseException:
        raw.close()
        proc.kill()
        temp.unlink(missing_ok=True)
        raise
    return PartitionRecord(part.name, part.dev, part.size, part.kind, final.name, sha.hexdigest(),
                           final.stat().st_size,                            codec,
                           time.perf_counter() - start)


def write_manifest(out_dir: Path, info: dict, access: Access, quiesce: Quiesce | None,
                   records: list[PartitionRecord]) -> Path:
    data = {"format": 1, "tool": f"Quasar for Windows {__version__}", "created": datetime.now().isoformat(),
            "device": info, "access": access.kind,
            "consistency": ("recovery (nothing mounted)" if not access.live else
                            "read-only /data" if quiesce and quiesce.data_readonly else "crash-consistent"),
            "partitions": [asdict(r) for r in records]}
    path = out_dir / MANIFEST
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def create_image(adb: Adb, serial: str, access: Access, parts: list[Partition], out_dir: Path,
                 compress: bool = True, method: str = "zstd", level_name: str = "fast", quiesce: bool = True,
                 on_progress: Progress | None = None, cancel: threading.Event | None = None,
                 log: Callable[[str], None] = lambda m: None) -> Path:
    """Image every selected partition into out_dir and write the manifest."""
    info = device_info(adb, serial)
    out_dir.mkdir(parents=True, exist_ok=True)
    records: list[PartitionRecord] = []
    guard = Quiesce(adb, serial, access, log) if quiesce else None
    # slot-less names only matter for the manifest; the live slot is recorded in info["slot"]
    if guard:
        guard.__enter__()
    try:
        for part in parts:
            log(f"Imaging {part.name}…")
            records.append(image_partition(adb, serial, access,             part, out_dir, compress, method, level_name,
                                           on_progress, cancel))
    finally:
        if guard:
            guard.__exit__(None, None, None)
    return write_manifest(out_dir, info, access, guard, records)


def upload_image(folder: Path, provider, passphrase: str = "", security: str = "enhanced",
                 on_progress: Callable[[float, str], None] = lambda f, t: None,
                 cancel: threading.Event | None = None) -> list[str]:
    """Upload every file of an image folder. Providers use flat names, so each file is
    prefixed with the folder name. With a passphrase each file is encrypted (.qsr) first."""
    from . import encryption

    cancel = cancel or threading.Event()
    load_manifest(folder)
    files = sorted(p for p in folder.iterdir() if p.is_file() and not p.name.endswith(".part"))
    total = sum(p.stat().st_size for p in files) or 1
    stage = folder / ".upload"
    stage.mkdir(exist_ok=True)
    done_bytes, locations = 0, []
    try:
        for f in files:
            if cancel.is_set():
                raise ImageError("Cancelled")
            staged = stage / f"{folder.name}__{f.name}"
            staged.unlink(missing_ok=True)
            if passphrase:
                staged = staged.with_name(staged.name + ".qsr")
                encryption.encrypt_file(f, staged, passphrase, security, lambda _f: None, cancel)
            else:
                try:
                    os.link(f, staged)
                except OSError:
                    shutil.copy2(f, staged)
            size = f.stat().st_size
            base = done_bytes
            res = provider.upload(
                staged, lambda sent, tot, b=base, s=size, n=f.name: on_progress(
                    (b + s * (sent / tot if tot else 1)) / total, f"Uploading {n}"), cancel)
            locations.append(res.location)
            done_bytes += size
            staged.unlink(missing_ok=True)
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    on_progress(1.0, "Done")
    return locations


def load_manifest(folder: Path) -> dict:
    path = folder / MANIFEST
    if not path.exists():
        raise ImageError(f"{MANIFEST} not found in {folder}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("format") != 1:
        raise ImageError("Unsupported image format")
    return data


def _open_in(path: Path, compression: str):
    f = open(path, "rb")
    if compression == "zstd":
        return zstandard.ZstdDecompressor().stream_reader(f), f
    if compression == "gzip":
        return gzip.GzipFile(fileobj=f, mode="rb"), f
    if compression == "bzip2":
        return bz2.BZ2File(f, "rb"), f
    if compression == "xz":
        return lzma.LZMAFile(f, "rb"), f
    if compression == "zip":
        zf = zipfile.ZipFile(f)
        return zf.open("image"), f
    return f, f


def verify_record(folder: Path, rec: dict, cancel: threading.Event | None = None) -> bool:
    """Re-hash a stored partition image against the manifest (no phone needed)."""
    reader, f = _open_in(folder / rec["file"], rec["compression"])
    sha, total = hashlib.sha256(), 0
    try:
        while chunk := reader.read(CHUNK):
            if cancel and cancel.is_set():
                raise ImageError("Cancelled")
            sha.update(chunk)
            total += len(chunk)
    finally:
        f.close()
    return total == rec["size"] and sha.hexdigest() == rec["sha256"]


def restore_blocker(access: Access, rec: dict, allow_bootchain: bool) -> str:
    kind = rec["kind"]
    if kind == "bootchain" and not allow_bootchain:
        return "Bootloader-chain partition: flashing the wrong one can permanently brick the phone."
    if access.live and base_name(rec["name"]) not in RESTORE_LIVE_SAFE and kind != "bootchain":
        return "In use by the running system. Boot into custom recovery to restore this partition."
    return ""


def check_device_match(manifest: dict, info: dict) -> str:
    saved = manifest.get("device", {})
    if saved.get("device") and info.get("device") and saved["device"] != info["device"]:
        return (f"This image is from '{saved['device']}' but the connected phone is "
                f"'{info['device']}'. Restoring across models will not work.")
    return ""


def restore_partition(adb: Adb, serial: str, access: Access, folder: Path, rec: dict,
                      on_progress: Progress | None = None, cancel: threading.Event | None = None) -> None:
    """Verify the stored image, write it to the phone, then read it back and compare hashes."""
    if not verify_record(folder, rec, cancel):
        raise ImageError(f"{rec['name']}: stored image is corrupt (hash mismatch). Nothing was written.")
    dev = rec["dev"]
    if access.kind == "recovery":
        adb.shell(serial, f"umount {dev} 2>/dev/null; true")
    _, mounts = adb.shell(serial, access.wrap(f"grep -c '^{dev} ' /proc/mounts; true"))
    if mounts.strip() not in ("", "0") and access.kind != "recovery":
        raise ImageError(f"{rec['name']} is mounted; restore from recovery instead.")
    size, done, start = rec["size"], 0, time.perf_counter()
    reader, f = _open_in(folder / rec["file"], rec["compression"])
    proc = adb.popen_in(serial, access.wrap(f"dd of={dev} bs={CHUNK} 2>/dev/null"))
    try:
        while chunk := reader.read(CHUNK):
            if cancel and cancel.is_set():
                raise ImageError("Cancelled - the partition may be partly written; re-run the restore.")
            proc.stdin.write(chunk)
            done += len(chunk)
            if on_progress:
                on_progress(rec["name"], done, size, done / max(time.perf_counter() - start, 1e-6))
        proc.stdin.close()
        proc.wait(timeout=600)
    except BaseException:
        proc.kill()
        raise
    finally:
        f.close()
    adb.shell(serial, access.wrap("sync"))
    sha, got = hashlib.sha256(), 0
    check = adb.popen_out(serial, access.wrap(f"dd if={dev} bs={CHUNK} count={(size + CHUNK - 1) // CHUNK} 2>/dev/null"))
    while got < size:
        chunk = check.stdout.read(min(CHUNK, size - got))
        if not chunk:
            break
        sha.update(chunk)
        got += len(chunk)
    check.kill()
    if got != size or sha.hexdigest() != rec["sha256"]:
        raise ImageError(f"{rec['name']}: read-back did not match what was written. Retry the restore.")


def restore_image(adb: Adb, serial: str, access: Access, folder: Path, names: list[str],
                  allow_bootchain: bool = False, on_progress: Progress | None = None,
                  cancel: threading.Event | None = None,
                  log: Callable[[str], None] = lambda m: None) -> list[str]:
    manifest = load_manifest(folder)
    mismatch = check_device_match(manifest, device_info(adb, serial))
    if mismatch:
        raise ImageError(mismatch)
    recs = [r for r in manifest["partitions"] if r["name"] in names]
    for rec in recs:  # refuse the whole job up front rather than half-restoring
        reason = restore_blocker(access, rec, allow_bootchain)
        if reason:
            raise ImageError(f"{rec['name']}: {reason}")
    for rec in recs:
        log(f"Verifying and restoring {rec['name']}…")
        restore_partition(adb, serial, access, folder, rec, on_progress, cancel)
    return [r["name"] for r in recs]
