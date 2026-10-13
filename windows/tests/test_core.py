import os
import threading
from pathlib import Path

import pytest

from quasar_win import adb, cloud, compression, encryption


@pytest.fixture()
def sample(tmp_path: Path) -> Path:
    path = tmp_path / "backup.ab"
    path.write_bytes((b"ANDROID BACKUP\n5\n1\nnone\n" + b"quasar " * 40000) + os.urandom(300_000))
    return path


@pytest.mark.parametrize("method", list(compression.METHODS))
def test_compression_roundtrip(method, sample, tmp_path):
    level = list(compression.METHODS[method].levels)[0]
    out = tmp_path / compression.output_name(sample, method)
    seen = []
    result = compression.compress(sample, out, method, level, progress=seen.append)
    assert result.original_size == sample.stat().st_size
    assert 0 < result.compressed_size < result.original_size
    assert seen and seen[-1] == pytest.approx(1.0)
    restored = compression.decompress(out, tmp_path / "restored")
    assert restored.read_bytes() == sample.read_bytes()


def test_compression_cancel_removes_partial_output(sample, tmp_path):
    cancel = threading.Event()
    cancel.set()
    out = tmp_path / "x.zst"
    with pytest.raises(compression.Cancelled):
        compression.compress(sample, out, "zstd", "fast", cancel=cancel)
    assert not out.exists()


def test_benchmark_collects_results(sample, tmp_path):
    results = compression.benchmark(sample, tmp_path / "bench",
                                    [("zstd", "fast"), ("tar.gz", "fast")], sample_bytes=100_000)
    assert [r.method for r in results] == ["zstd", "tar.gz"]
    assert all(r.original_size == 100_000 and r.decompress_seconds is not None for r in results)
    assert not list((tmp_path / "bench").glob("*.zst"))


@pytest.mark.parametrize("level", ["standard", "enhanced"])
def test_encryption_roundtrip(level, sample, tmp_path):
    enc, dec = tmp_path / "a.qsr", tmp_path / "a.out"
    encryption.encrypt_file(sample, enc, "correct horse", level)
    assert enc.read_bytes()[:4] == b"QSR1"
    encryption.decrypt_file(enc, dec, "correct horse")
    assert dec.read_bytes() == sample.read_bytes()


def test_encryption_multi_chunk_and_empty(tmp_path):
    big = tmp_path / "big.bin"
    big.write_bytes(os.urandom(encryption.CHUNK * 2))  # exact multiple of the chunk size
    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    for src in (big, empty):
        enc, dec = tmp_path / (src.name + ".qsr"), tmp_path / (src.name + ".out")
        encryption.encrypt_file(src, enc, "pw")
        encryption.decrypt_file(enc, dec, "pw")
        assert dec.read_bytes() == src.read_bytes()


def test_encryption_detects_wrong_password_tamper_and_truncation(sample, tmp_path):
    enc = tmp_path / "a.qsr"
    encryption.encrypt_file(sample, enc, "pw")
    with pytest.raises(encryption.DecryptionError):
        encryption.decrypt_file(enc, tmp_path / "o1", "nope")
    assert not (tmp_path / "o1").exists()

    data = bytearray(enc.read_bytes())
    data[len(data) // 2] ^= 1
    bad = tmp_path / "bad.qsr"
    bad.write_bytes(bytes(data))
    with pytest.raises(encryption.DecryptionError):
        encryption.decrypt_file(bad, tmp_path / "o2", "pw")

    big = tmp_path / "big.bin"
    big.write_bytes(os.urandom(encryption.CHUNK * 2 + 10))
    encryption.encrypt_file(big, enc, "pw")
    blob = enc.read_bytes()
    first_record = encryption.HEADER.size + 5 + int.from_bytes(
        blob[encryption.HEADER.size + 1:encryption.HEADER.size + 5], "big")
    enc.write_bytes(blob[:first_record])  # drop later chunks
    with pytest.raises(encryption.DecryptionError):
        encryption.decrypt_file(enc, tmp_path / "o3", "pw")


def test_parse_devices():
    out = ("List of devices attached\n"
           "R58M123 device usb:1-1 product:x model:Pixel_7 device:y transport_id:1\n"
           "ABC123 unauthorized usb:1-2 transport_id:2\n")
    devices = adb.parse_devices(out)
    assert [d.state for d in devices] == ["device", "unauthorized"]
    assert devices[0].ready and devices[0].title == "Pixel 7"
    assert not devices[1].ready


def test_backup_command_flags(tmp_path):
    cmd = adb.Adb(Path("adb.exe")).backup_command(tmp_path / "o.ab", "S1", True, False, False)
    assert cmd[1:3] == ["-s", "S1"] and "-apk" in cmd and "-noshared" in cmd and "-nosystem" in cmd


def test_run_backup_with_fake_adb(tmp_path):
    fake = tmp_path / "fake_adb.bat"
    fake.write_text('@echo off\r\n'
                    'set out=\r\n'
                    ':loop\r\nif "%~1"=="-f" set out=%~2\r\nshift\r\nif not "%~1"=="" goto loop\r\n'
                    '(echo ANDROID BACKUP& echo 5& echo 1& echo none) > "%out%"\r\n'
                    'fsutil file createnew "%out%.pad" 5000 >nul\r\n'
                    'type "%out%.pad" >> "%out%"\r\n')
    progress = []
    outcome = adb.Adb(fake).run_backup(tmp_path / "o.ab", "S1", True, True, True,
                                       lambda s, t: progress.append(s), threading.Event())
    assert outcome.valid and not outcome.looks_empty and outcome.verdict() == ""
    assert progress


def test_empty_backup_is_flagged(tmp_path):
    out = tmp_path / "e.ab"
    out.write_bytes(b"ANDROID BACKUP\n5\n1\nnone\n")
    outcome = adb.BackupOutcome(out, out.stat().st_size, 1.0, False, 0, "", True)
    assert "no data" in outcome.verdict()


def test_local_folder_upload(sample, tmp_path):
    provider = cloud.make_provider("local_folder", {"path": str(tmp_path / "cloud")})
    seen = []
    result = provider.upload(sample, lambda s, t: seen.append((s, t)), threading.Event())
    assert (tmp_path / "cloud" / sample.name).read_bytes() == sample.read_bytes()
    assert seen[-1][0] == seen[-1][1] == result.size and result.speed_mbps > 0


def test_missing_provider_settings_raise():
    with pytest.raises(cloud.UploadError):
        cloud.make_provider("dropbox", {}).test()
