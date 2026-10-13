"""ADB discovery, device inspection, guided backup and APK install."""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import threading
import time
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .config import app_dir

PLATFORM_TOOLS_URL = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
BACKUP_MAGIC = b"ANDROID BACKUP"


class AdbError(Exception):
    pass


@dataclass
class Device:
    serial: str
    state: str  # device | unauthorized | offline | ...
    model: str = ""
    product: str = ""
    android: str = ""
    sdk: int = 0
    extra: dict = field(default_factory=dict)

    @property
    def ready(self) -> bool:
        return self.state == "device"

    @property
    def title(self) -> str:
        return self.model.replace("_", " ") or self.serial

    @property
    def backup_warning(self) -> str:
        if self.sdk >= 31:
            return ("Android 12+ restricts 'adb backup'. Many apps opt out and some devices "
                    "return an almost empty file. Quasar will tell you how much was captured.")
        if self.sdk >= 23 and self.sdk:
            return "This Android version supports adb backup for apps that allow backups."
        return ""


def platform_tools_dir() -> Path:
    return app_dir() / "platform-tools"


def find_adb() -> Path | None:
    candidates: list[Path] = [platform_tools_dir() / "adb.exe"]
    for env in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        if os.environ.get(env):
            candidates.append(Path(os.environ[env]) / "platform-tools" / "adb.exe")
    found = shutil.which("adb")
    if found:
        candidates.insert(0, Path(found))
    return next((c for c in candidates if c.exists()), None)


def download_platform_tools(progress: Callable[[float], None] | None = None,
                            url: str = PLATFORM_TOOLS_URL) -> Path:
    """Download Google's official platform-tools and unpack them under %APPDATA%."""
    buffer = io.BytesIO()
    with urllib.request.urlopen(url, timeout=30) as response:
        total = int(response.headers.get("Content-Length") or 0)
        while chunk := response.read(256 * 1024):
            buffer.write(chunk)
            if progress and total:
                progress(buffer.tell() / total)
    target = app_dir()
    existing = platform_tools_dir()
    if existing.exists():
        shutil.rmtree(existing, ignore_errors=True)
    with zipfile.ZipFile(buffer) as archive:
        archive.extractall(target)
    adb = existing / "adb.exe"
    if not adb.exists():
        raise AdbError("platform-tools archive did not contain adb.exe")
    return adb


def parse_devices(output: str) -> list[Device]:
    devices: list[Device] = []
    for line in output.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 2 or line.startswith("*"):
            continue
        info = dict(p.split(":", 1) for p in parts[2:] if ":" in p)
        devices.append(Device(parts[0], parts[1], model=info.get("model", ""),
                              product=info.get("product", "")))
    return devices


class Adb:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or find_adb()
        self._info: dict[str, tuple[str, str, int]] = {}

    @property
    def available(self) -> bool:
        return bool(self.path and Path(self.path).exists())

    def _run(self, *args: str, serial: str | None = None, timeout: float = 20) -> str:
        if not self.available:
            raise AdbError("ADB is not installed yet")
        cmd = [str(self.path)] + (["-s", serial] if serial else []) + list(args)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                                  creationflags=CREATE_NO_WINDOW)
        except subprocess.TimeoutExpired as exc:
            raise AdbError(f"adb {' '.join(args)} timed out") from exc
        if proc.returncode != 0:
            raise AdbError((proc.stderr or proc.stdout).strip() or f"adb exited {proc.returncode}")
        return proc.stdout

    def start_server(self) -> None:
        self._run("start-server", timeout=30)

    def devices(self) -> list[Device]:
        devices = parse_devices(self._run("devices", "-l"))
        for device in devices:
            if not device.ready:
                continue
            cached = self._info.get(device.serial)
            if cached:
                device.model, device.android, device.sdk = cached
            else:
                self._inspect(device)
                self._info[device.serial] = (device.model, device.android, device.sdk)
        return devices

    def _inspect(self, device: Device) -> None:
        def prop(name: str) -> str:
            try:
                return self._run("shell", "getprop", name, serial=device.serial, timeout=8).strip()
            except AdbError:
                return ""

        device.model = prop("ro.product.model") or device.model
        device.android = prop("ro.build.version.release")
        sdk = prop("ro.build.version.sdk")
        device.sdk = int(sdk) if sdk.isdigit() else 0

    def install_apk(self, apk: Path, serial: str) -> str:
        return self._run("install", "-r", str(apk), serial=serial, timeout=300).strip()

    def shell(self, serial: str, command: str, timeout: float = 60) -> tuple[int, str]:
        """Run a device shell command; returns (exit code, combined output) without raising."""
        if not self.available:
            raise AdbError("ADB is not installed yet")
        try:
            proc = subprocess.run([str(self.path), "-s", serial, "shell", "-T", command],
                                  capture_output=True, text=True, timeout=timeout,
                                  errors="replace", creationflags=CREATE_NO_WINDOW)
        except subprocess.TimeoutExpired as exc:
            raise AdbError(f"timed out: {command[:60]}") from exc
        return proc.returncode, (proc.stdout + proc.stderr).strip()

    def popen_out(self, serial: str, command: str) -> subprocess.Popen:
        """Binary-safe stream of a device command's stdout (adb exec-out)."""
        return subprocess.Popen([str(self.path), "-s", serial, "exec-out", command],
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                creationflags=CREATE_NO_WINDOW)

    def popen_in(self, serial: str, command: str) -> subprocess.Popen:
        """Feed bytes to a device command's stdin (no pty, so the stream is raw)."""
        return subprocess.Popen([str(self.path), "-s", serial, "shell", "-T", command],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, creationflags=CREATE_NO_WINDOW)

    def reboot(self, serial: str, target: str = "") -> None:
        self._run("reboot", *([target] if target else []), serial=serial, timeout=30)

    def fastboot_path(self) -> Path | None:
        if not self.path:
            return None
        exe = Path(self.path).with_name("fastboot.exe")
        return exe if exe.exists() else None

    def fastboot_boot(self, image: Path, timeout: float = 120) -> str:
        """Temporarily boot a recovery image (nothing is flashed to the phone)."""
        fb = self.fastboot_path()
        if not fb:
            raise AdbError("fastboot.exe was not found next to adb (reinstall platform-tools)")
        proc = subprocess.run([str(fb), "boot", str(image)], capture_output=True, text=True,
                              timeout=timeout, creationflags=CREATE_NO_WINDOW)
        if proc.returncode != 0:
            raise AdbError((proc.stderr or proc.stdout).strip() or "fastboot boot failed")
        return (proc.stderr + proc.stdout).strip()

    def fastboot_devices(self) -> list[str]:
        fb = self.fastboot_path()
        if not fb:
            return []
        proc = subprocess.run([str(fb), "devices"], capture_output=True, text=True, timeout=15,
                              creationflags=CREATE_NO_WINDOW)
        return [ln.split()[0] for ln in proc.stdout.splitlines() if ln.strip()]

    def backup_command(self, out_file: Path, serial: str, apks: bool, shared: bool,
                       system: bool) -> list[str]:
        return [str(self.path), "-s", serial, "backup", "-f", str(out_file), "-all",
                "-apk" if apks else "-noapk",
                "-shared" if shared else "-noshared",
                "-system" if system else "-nosystem"]

    def run_backup(self, out_file: Path, serial: str, apks: bool, shared: bool, system: bool,
                   on_progress: Callable[[int, float], None],
                   cancel: threading.Event) -> "BackupOutcome":
        """Run `adb backup` and poll the output size. Blocks until it finishes."""
        if not self.available:
            raise AdbError("ADB is not installed yet")
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.unlink(missing_ok=True)
        cmd = self.backup_command(out_file, serial, apks, shared, system)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                creationflags=CREATE_NO_WINDOW)
        start = time.perf_counter()
        cancelled = False
        while proc.poll() is None:
            if cancel.is_set():
                proc.terminate()
                cancelled = True
                break
            size = out_file.stat().st_size if out_file.exists() else 0
            on_progress(size, time.perf_counter() - start)
            time.sleep(0.5)
        try:
            stdout, stderr = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
        size = out_file.stat().st_size if out_file.exists() else 0
        on_progress(size, time.perf_counter() - start)
        return BackupOutcome(out_file, size, time.perf_counter() - start, cancelled,
                             proc.returncode or 0, (stderr or stdout or "").strip(),
                             _has_backup_header(out_file))


@dataclass
class BackupOutcome:
    path: Path
    size: int
    seconds: float
    cancelled: bool
    returncode: int
    message: str
    valid: bool

    @property
    def looks_empty(self) -> bool:
        # an accepted-but-empty backup is only the ~50 byte header
        return self.size < 1024

    def verdict(self) -> str:
        if self.cancelled:
            return "Backup was cancelled."
        if self.looks_empty:
            return ("The phone produced no data. Common causes: the backup prompt was dismissed "
                    "on the phone, the screen locked, or Android 12+ blocked the backup.")
        if not self.valid:
            return "The file does not look like an Android backup (missing header)."
        if self.returncode != 0:
            return f"adb reported an error: {self.message}"
        return ""


def _has_backup_header(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(len(BACKUP_MAGIC)) == BACKUP_MAGIC
    except OSError:
        return False
