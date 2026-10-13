"""Dual-layer authenticated encryption compatible in spirit with the Android app.

Layer 1: AES-256-GCM.  Layer 2 (optional): XChaCha20-Poly1305.
Keys come from the passphrase via scrypt. Data is processed in 1 MiB chunks, each
authenticated with its index and a "final chunk" flag so truncation and reordering
are detected.
"""
from __future__ import annotations

import os
import struct
import threading
from pathlib import Path
from typing import Callable

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from nacl import bindings as sodium

MAGIC = b"QSR1"
CHUNK = 1024 * 1024
SCRYPT_LOG_N, SCRYPT_R, SCRYPT_P = 15, 8, 1
SECURITY_LEVELS = {
    "standard": "AES-256-GCM",
    "enhanced": "AES-256-GCM + XChaCha20-Poly1305",
}
HEADER = struct.Struct(">4sBBBBB16s8s")  # magic, version, layers, log_n, r, p, salt, nonce prefix

Progress = Callable[[float], None]


class DecryptionError(Exception):
    pass


def _derive(passphrase: str, salt: bytes, log_n: int, r: int, p: int) -> tuple[bytes, bytes]:
    key = Scrypt(salt=salt, length=64, n=2 ** log_n, r=r, p=p).derive(passphrase.encode("utf-8"))
    return key[:32], key[32:]


def _aad(header: bytes, index: int, final: bool) -> bytes:
    return header + struct.pack(">QB", index, 1 if final else 0)


def encrypt_file(src: Path, dst: Path, passphrase: str, level: str = "enhanced",
                 progress: Progress | None = None,
                 cancel: threading.Event | None = None) -> int:
    if not passphrase:
        raise ValueError("A passphrase is required")
    layers = 2 if level == "enhanced" else 1
    salt, prefix = os.urandom(16), os.urandom(8)
    header = HEADER.pack(MAGIC, 1, layers, SCRYPT_LOG_N, SCRYPT_R, SCRYPT_P, salt, prefix)
    aes_key, xchacha_key = _derive(passphrase, salt, SCRYPT_LOG_N, SCRYPT_R, SCRYPT_P)
    aes = AESGCM(aes_key)
    total = max(src.stat().st_size, 1)
    done = 0
    try:
        with open(src, "rb") as fin, open(dst, "wb") as fout:
            fout.write(header)
            index = 0
            current = fin.read(CHUNK)
            while True:
                following = fin.read(CHUNK) if len(current) == CHUNK else b""
                final = not following
                aad = _aad(header, index, final)
                nonce = prefix + struct.pack(">I", index & 0xFFFFFFFF)
                blob = aes.encrypt(nonce, current, aad)
                if layers == 2:
                    outer = os.urandom(24)
                    blob = outer + sodium.crypto_aead_xchacha20poly1305_ietf_encrypt(
                        blob, aad, outer, xchacha_key)
                fout.write(struct.pack(">BI", 1 if final else 0, len(blob)) + blob)
                done += len(current)
                if progress:
                    progress(min(done / total, 1.0))
                if cancel and cancel.is_set():
                    raise InterruptedError("Cancelled")
                if final:
                    break
                current, index = following, index + 1
    except BaseException:
        dst.unlink(missing_ok=True)
        raise
    return dst.stat().st_size


def decrypt_file(src: Path, dst: Path | None, passphrase: str,
                 progress: Progress | None = None) -> int:
    """Decrypt src into dst. With dst=None the data is authenticated and discarded."""
    total = max(src.stat().st_size, 1)
    written = 0
    try:
        with open(src, "rb") as fin, (open(dst, "wb") if dst else open(os.devnull, "wb")) as fout:
            raw = fin.read(HEADER.size)
            if len(raw) < HEADER.size:
                raise DecryptionError("File is too short to be a Quasar archive")
            magic, version, layers, log_n, r, p, salt, prefix = HEADER.unpack(raw)
            if magic != MAGIC or version != 1:
                raise DecryptionError("Not a Quasar encrypted file")
            aes_key, xchacha_key = _derive(passphrase, salt, log_n, r, p)
            aes = AESGCM(aes_key)
            index, seen_final = 0, False
            while True:
                meta = fin.read(5)
                if not meta:
                    break
                if seen_final or len(meta) < 5:
                    raise DecryptionError("Unexpected data after the final block")
                flag, length = struct.unpack(">BI", meta)
                blob = fin.read(length)
                if len(blob) != length:
                    raise DecryptionError("File is truncated")
                final = bool(flag)
                aad = _aad(raw, index, final)
                try:
                    if layers == 2:
                        blob = sodium.crypto_aead_xchacha20poly1305_ietf_decrypt(
                            blob[24:], aad, blob[:24], xchacha_key)
                    nonce = prefix + struct.pack(">I", index & 0xFFFFFFFF)
                    plain = aes.decrypt(nonce, blob, aad)
                    fout.write(plain)
                    written += len(plain)
                except Exception as exc:
                    raise DecryptionError("Wrong passphrase or corrupted data") from exc
                seen_final = final
                index += 1
                if progress:
                    progress(min(fin.tell() / total, 1.0))
            if not seen_final:
                raise DecryptionError("File is truncated")
    except BaseException:
        if dst:
            dst.unlink(missing_ok=True)
        raise
    return written


def verify_file(src: Path, passphrase: str, progress: Progress | None = None) -> bool:
    """True if every block authenticates with this passphrase."""
    decrypt_file(src, None, passphrase, progress)
    return True
