import hashlib
import io
import os
import re
import shlex

import pytest

from quasar_win import image
from quasar_win.image import Access, ImageError, Partition


class FakeProc:
    def __init__(self, data=b""):
        self.stdout = io.BytesIO(data)
        self.stdin = self
        self.sink = bytearray()
        self.returncode = 0

    def write(self, b):
        self.sink += b

    def close(self):
        pass

    def wait(self, timeout=None):
        return 0

    def kill(self):
        pass


class FakeAdb:
    """Simulates a rooted phone: partitions are byte strings keyed by device path."""

    available = True

    def devices(self):
        from quasar_win.adb import Device
        return [Device("S1", "device", model="Pixel_7")]

    def __init__(self, root=True, ro_ok=True, short=None):
        rng = os.urandom
        self.disk = {"/dev/block/sda1": rng(2_500_000), "/dev/block/sda2": b"\0" * 1_048_576 + rng(10),
                     "/dev/block/sda3": rng(4096)}
        self.names = {"boot": "/dev/block/sda1", "userdata": "/dev/block/sda2", "xbl": "/dev/block/sda3"}
        self.root, self.ro_ok, self.short = root, ro_ok, short
        self.log = []
        self.mounts = "/dev/block/dm-9 /data f2fs rw,seclabel 0 0"

    def _inner(self, cmd):
        m = re.match(r"su -c (.*)$", cmd)
        return shlex.split(m.group(1))[0] if m else cmd

    def shell(self, serial, cmd, timeout=60):
        self.log.append(cmd)
        inner = self._inner(cmd)
        if inner == "id -u":
            return (0, "0") if self.root else (1, "")
        if cmd == "su -c id -u":
            return (0, "0") if self.root else (1, "su: not found")
        if inner.startswith("getprop ro.twrp"):
            return 0, ""
        if inner.startswith("getprop"):
            return 0, {"ro.product.device": "pixel7"}.get(inner.split()[1], "x")
        if "by-name" in inner:
            return 0, "\n".join(f"{n}|{d}|{len(self.disk[d])}" for n, d in self.names.items())
        if inner.startswith("grep ' /data '"):
            return 0, self.mounts
        if inner.startswith("mount -o remount,ro") and self.ro_ok:
            self.mounts = self.mounts.replace(" rw,", " ro,")
        if inner.startswith("mount -o remount,rw"):
            self.mounts = self.mounts.replace(" ro,", " rw,")
        if inner.startswith("grep -c"):
            return 0, "0"
        return 0, ""

    def popen_out(self, serial, cmd):
        dev = re.search(r"if=(\S+)", cmd).group(1)
        data = self.disk[dev]
        if self.short:
            data = data[: self.short]
        count = re.search(r"count=(\d+)", cmd)
        if count:
            data = data[: int(count.group(1)) * image.CHUNK]
        return FakeProc(data)

    def popen_in(self, serial, cmd):
        dev = re.search(r"of=(\S+)", cmd).group(1)
        proc = FakeProc()
        self.target = (dev, proc)
        return proc

    def commit(self):
        dev, proc = self.target
        self.disk[dev] = bytes(proc.sink)


class RestoringAdb(FakeAdb):
    def popen_in(self, serial, cmd):
        proc = super().popen_in(serial, cmd)
        orig = proc.close

        def close():
            self.commit()
        proc.close = close
        return proc


def test_classify_and_defaults():
    assert image.classify("boot_a") == "core"
    assert image.classify("xbl_b") == "bootchain"
    assert image.classify("userdata") == "data"
    assert image.classify("modemst1") == "radio"
    assert Partition("xbl", "/dev/x", 10).selected is False
    assert Partition("boot", "/dev/x", 10).selected is True


def test_detect_access_modes():
    assert image.detect_access(FakeAdb(), "s").kind == "adb-root"
    magisk = FakeAdb()
    magisk.shell = lambda s, c, timeout=60: (0, "0") if c == "su -c id -u" else (1, "")
    assert image.detect_access(magisk, "s").kind == "magisk"
    with pytest.raises(ImageError):
        image.detect_access(FakeAdb(root=False), "s")


def test_list_partitions():
    parts = image.list_partitions(FakeAdb(), "s", Access("magisk", True))
    assert {p.name for p in parts} == {"boot", "userdata", "xbl"}


@pytest.mark.parametrize("compress", [True, False])
def test_image_roundtrip_and_manifest(tmp_path, compress):
    adb = FakeAdb()
    access = Access("magisk", True)
    parts = [p for p in image.list_partitions(adb, "s", access) if p.selected]
    mf = image.create_image(adb, "s", access, parts, tmp_path / "img", compress=compress)
    data = image.load_manifest(mf.parent)
    assert data["consistency"] == "read-only /data"
    recs = {r["name"]: r for r in data["partitions"]}
    assert set(recs) == {"boot", "userdata"}
    assert recs["boot"]["sha256"] == hashlib.sha256(adb.disk["/dev/block/sda1"]).hexdigest()
    assert all(image.verify_record(mf.parent, r) for r in recs.values())
    # /data and the framework are put back afterwards
    assert "rw," in adb.mounts
    assert any("start" == adb._inner(c) for c in adb.log)


@pytest.mark.parametrize("method", ["zstd", "zstd-ultra", "tar.gz", "tar.bz2", "tar.xz", "zip"])
def test_image_every_codec_verifies(tmp_path, method):
    adb = FakeAdb()
    access = Access("recovery", False)
    parts = [p for p in image.list_partitions(adb, "s", access) if p.selected]
    mf = image.create_image(adb, "s", access, parts, tmp_path / "img", method=method,
                            level_name="fast", quiesce=False)
    recs = image.load_manifest(mf.parent)["partitions"]
    assert all(image.verify_record(mf.parent, r) for r in recs)
    assert all(r["file"].endswith(image.IMAGE_METHODS[method][1]) for r in recs)


def test_image_rejects_7z(tmp_path):
    adb = FakeAdb()
    access = Access("recovery", False)
    parts = [p for p in image.list_partitions(adb, "s", access) if p.selected]
    with pytest.raises(ImageError):
        image.create_image(adb, "s", access, parts, tmp_path / "img", method="7z", quiesce=False)


def test_upload_image_plain_and_encrypted(tmp_path):
    from quasar_win.cloud import make_provider
    from quasar_win import encryption

    adb = FakeAdb()
    access = Access("recovery", False)
    parts = [p for p in image.list_partitions(adb, "s", access) if p.selected]
    folder = image.create_image(adb, "s", access, parts, tmp_path / "img", quiesce=False).parent
    prov = make_provider("local_folder", {"path": str(tmp_path / "cloud")})

    seen = []
    image.upload_image(folder, prov, on_progress=lambda f, t: seen.append(f))
    names = sorted(p.name for p in (tmp_path / "cloud").iterdir())
    assert f"img__{image.MANIFEST}" in names and seen[-1] == 1.0
    assert not (folder / ".upload").exists()

    image.upload_image(folder, prov, passphrase="correct horse", )
    enc = tmp_path / "cloud" / "img__boot.img.zst.qsr"
    out = tmp_path / "dec"
    encryption.decrypt_file(enc, out, "correct horse")
    assert out.read_bytes() == (folder / "boot.img.zst").read_bytes()


def test_truncated_transfer_is_detected(tmp_path):
    adb = FakeAdb(short=1000)
    part = Partition("boot", "/dev/block/sda1", len(adb.disk["/dev/block/sda1"]))
    with pytest.raises(ImageError, match="cut short"):
        image.image_partition(adb, "s", Access("recovery", False), part, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_quiesce_falls_back_when_ro_refused(tmp_path):
    adb = FakeAdb(ro_ok=False)
    q = image.Quiesce(adb, "s", Access("magisk", True))
    with q:
        assert q.framework_stopped and not q.data_readonly
    assert "rw," in adb.mounts


def test_restore_roundtrip_and_safety(tmp_path):
    adb = RestoringAdb()
    recovery = Access("recovery", False)
    parts = [p for p in image.list_partitions(adb, "s", recovery) if p.selected]
    folder = image.create_image(adb, "s", recovery, parts, tmp_path / "img", quiesce=False).parent
    original = adb.disk["/dev/block/sda1"]
    adb.disk["/dev/block/sda1"] = b"corrupted" * 100
    image.restore_image(adb, "s", recovery, folder, ["boot", "userdata"])
    assert adb.disk["/dev/block/sda1"] == original

    live = Access("magisk", True)
    with pytest.raises(ImageError, match="recovery"):
        image.restore_image(adb, "s", live, folder, ["userdata"])
    manifest = image.load_manifest(folder)
    xbl = {"name": "xbl", "kind": "bootchain"}
    assert "brick" in image.restore_blocker(recovery, xbl, False)
    assert image.restore_blocker(recovery, xbl, True) == ""
    assert image.check_device_match(manifest, {"device": "other"})


def test_corrupt_image_is_never_written(tmp_path):
    adb = RestoringAdb()
    recovery = Access("recovery", False)
    part = Partition("boot", "/dev/block/sda1", len(adb.disk["/dev/block/sda1"]))
    mf = image.create_image(adb, "s", recovery, [part], tmp_path / "img", compress=False, quiesce=False)
    before = adb.disk["/dev/block/sda1"]
    f = mf.parent / "boot.img"
    blob = bytearray(f.read_bytes())
    blob[100] ^= 0xFF
    f.write_bytes(bytes(blob))
    with pytest.raises(ImageError, match="corrupt"):
        image.restore_image(adb, "s", recovery, mf.parent, ["boot"])
    assert adb.disk["/dev/block/sda1"] == before
