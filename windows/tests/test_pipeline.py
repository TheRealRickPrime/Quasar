import os
import threading

from quasar_win import cloud, encryption
from quasar_win.history import History
from quasar_win.pipeline import PipelineOptions, run_pipeline


def test_full_pipeline_compress_encrypt_upload(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    raw = tmp_path / "phone.ab"
    payload = b"ANDROID BACKUP\n5\n1\nnone\n" + b"data " * 100_000 + os.urandom(50_000)
    raw.write_bytes(payload)
    provider = cloud.make_provider("local_folder", {"path": str(tmp_path / "cloud")})
    steps = []
    result = run_pipeline(
        raw, PipelineOptions(compression="zstd", level="fast", passphrase="pw", provider=provider),
        lambda f, t: steps.append((f, t)), threading.Event(), History())

    assert [s.name.split(" - ")[0] for s in result.stages] == ["Compress", "Encrypt", "Upload"]
    assert not raw.exists()  # unencrypted original removed once the encrypted copy verified
    assert result.final_path.name == "phone.ab.zst.qsr"
    uploaded = tmp_path / "cloud" / result.final_path.name
    assert uploaded.read_bytes() == result.final_path.read_bytes()
    assert steps[-1] == (1.0, "Done")
    assert [r["kind"] for r in History().all()] == ["compress", "upload"]

    from quasar_win import compression
    dec = tmp_path / "phone.ab.zst"
    encryption.decrypt_file(uploaded, dec, "pw")
    assert compression.decompress(dec, tmp_path / "out").read_bytes() == payload


def test_pipeline_without_options_is_noop(tmp_path):
    raw = tmp_path / "a.ab"
    raw.write_bytes(b"ANDROID BACKUP\n" + b"x" * 5000)
    result = run_pipeline(raw, PipelineOptions(), lambda f, t: None, threading.Event())
    assert result.final_path == raw and raw.exists() and result.stages == []
