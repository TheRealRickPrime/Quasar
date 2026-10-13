"""Cloud upload providers matching the Android app (Drive, Dropbox, OneDrive, S3)."""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import requests

Progress = Callable[[int, int], None]  # bytes sent, total bytes


class UploadError(Exception):
    pass


@dataclass
class UploadResult:
    provider: str
    name: str
    size: int
    seconds: float
    location: str = ""

    @property
    def speed_mbps(self) -> float:
        """Megabits per second, the unit people compare network speeds in."""
        return (self.size * 8 / 1_000_000) / self.seconds if self.seconds > 0 else 0.0

    @property
    def speed_mb_s(self) -> float:
        return (self.size / 1_048_576) / self.seconds if self.seconds > 0 else 0.0


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    secret: bool = False
    placeholder: str = ""


class Provider:
    key = ""
    label = ""
    fields: tuple[Field, ...] = ()
    help = ""

    def __init__(self, config: dict[str, str]) -> None:
        self.config = config

    def test(self) -> str:
        raise NotImplementedError

    def upload(self, path: Path, progress: Progress, cancel: threading.Event) -> UploadResult:
        raise NotImplementedError

    def _require(self, *keys: str) -> None:
        missing = [k for k in keys if not self.config.get(k)]
        if missing:
            raise UploadError("Missing setting: " + ", ".join(missing))

    @staticmethod
    def _chunks(path: Path, size: int, cancel: threading.Event):
        total = path.stat().st_size
        with open(path, "rb") as f:
            offset = 0
            while True:
                if cancel.is_set():
                    raise UploadError("Upload cancelled")
                data = f.read(size)
                if not data and offset > 0:
                    return
                yield offset, data, total
                offset += len(data)
                if offset >= total:
                    return


def _check(response: requests.Response, ok: tuple[int, ...] = (200, 201)) -> requests.Response:
    if response.status_code not in ok:
        raise UploadError(f"HTTP {response.status_code}: {response.text[:300]}")
    return response


class LocalFolder(Provider):
    key, label = "local_folder", "Local / synced folder"
    fields = (Field("path", "Folder", placeholder=r"D:\QuasarCloud  (or a OneDrive/Dropbox folder)"),)
    help = "Copies to a folder. Point it at a synced cloud folder, or use it to test the pipeline."

    def test(self) -> str:
        self._require("path")
        Path(self.config["path"]).mkdir(parents=True, exist_ok=True)
        return f"Folder ready: {self.config['path']}"

    def upload(self, path, progress, cancel):
        self._require("path")
        dest_dir = Path(self.config["path"])
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / path.name
        total, sent, start = path.stat().st_size, 0, time.perf_counter()
        with open(path, "rb") as fin, open(dest, "wb") as fout:
            while chunk := fin.read(4 * 1024 * 1024):
                if cancel.is_set():
                    fout.close()
                    dest.unlink(missing_ok=True)
                    raise UploadError("Upload cancelled")
                fout.write(chunk)
                sent += len(chunk)
                progress(sent, total)
        return UploadResult(self.key, path.name, total, time.perf_counter() - start, str(dest))


class AwsS3(Provider):
    key, label = "aws_s3", "AWS S3"
    fields = (Field("access_key", "Access key ID"), Field("secret_key", "Secret access key", True),
              Field("region", "Region", placeholder="us-east-1"), Field("bucket", "Bucket"))
    help = "Uses an IAM key with s3:PutObject on the bucket."

    def _client(self):
        import boto3
        self._require("access_key", "secret_key", "bucket")
        return boto3.client("s3", aws_access_key_id=self.config["access_key"],
                            aws_secret_access_key=self.config["secret_key"],
                            region_name=self.config.get("region") or "us-east-1")

    def test(self) -> str:
        try:
            self._client().head_bucket(Bucket=self.config["bucket"])
        except Exception as exc:
            raise UploadError(str(exc)) from exc
        return f"Bucket '{self.config['bucket']}' is reachable"

    def upload(self, path, progress, cancel):
        client = self._client()
        total, sent = path.stat().st_size, 0
        key = f"quasar/{path.name}"
        start = time.perf_counter()

        def callback(n: int) -> None:
            nonlocal sent
            if cancel.is_set():
                raise UploadError("Upload cancelled")
            sent += n
            progress(sent, total)

        try:
            client.upload_file(str(path), self.config["bucket"], key, Callback=callback)
        except UploadError:
            raise
        except Exception as exc:
            raise UploadError(str(exc)) from exc
        return UploadResult(self.key, path.name, total, time.perf_counter() - start,
                            f"s3://{self.config['bucket']}/{key}")


class Dropbox(Provider):
    key, label = "dropbox", "Dropbox"
    fields = (Field("token", "Access token", True),)
    help = "Create an app at dropbox.com/developers with files.content.write, then generate a token."
    CHUNK = 8 * 1024 * 1024

    def _headers(self, arg: dict | None = None) -> dict:
        headers = {"Authorization": f"Bearer {self.config['token']}"}
        if arg is not None:
            headers["Dropbox-API-Arg"] = json.dumps(arg)
            headers["Content-Type"] = "application/octet-stream"
        return headers

    def test(self) -> str:
        self._require("token")
        r = _check(requests.post("https://api.dropboxapi.com/2/users/get_current_account",
                                 headers=self._headers(), timeout=20))
        return f"Connected as {r.json().get('name', {}).get('display_name', 'Dropbox user')}"

    def upload(self, path, progress, cancel):
        self._require("token")
        base = "https://content.dropboxapi.com/2/files/"
        start = time.perf_counter()
        session = None
        total = path.stat().st_size
        for offset, data, _ in self._chunks(path, self.CHUNK, cancel):
            if session is None:
                r = _check(requests.post(base + "upload_session/start",
                                         headers=self._headers({"close": False}),
                                         data=data, timeout=120))
                session = r.json()["session_id"]
            else:
                cursor = {"session_id": session, "offset": offset}
                _check(requests.post(base + "upload_session/append_v2",
                                     headers=self._headers({"cursor": cursor, "close": False}),
                                     data=data, timeout=120))
            progress(offset + len(data), total)
        cursor = {"session_id": session, "offset": total}
        commit = {"path": f"/Quasar/{path.name}", "mode": "add", "autorename": True}
        _check(requests.post(base + "upload_session/finish",
                             headers=self._headers({"cursor": cursor, "commit": commit}),
                             data=b"", timeout=120))
        return UploadResult(self.key, path.name, total, time.perf_counter() - start,
                            f"/Quasar/{path.name}")


class GoogleDrive(Provider):
    key, label = "google_drive", "Google Drive"
    fields = (Field("token", "OAuth access token", True),)
    help = "Needs an OAuth token with the drive.file scope (e.g. from the OAuth Playground)."
    CHUNK = 8 * 1024 * 1024  # multiple of 256 KiB

    def test(self) -> str:
        self._require("token")
        r = _check(requests.get("https://www.googleapis.com/drive/v3/about?fields=user",
                                headers={"Authorization": f"Bearer {self.config['token']}"},
                                timeout=20))
        return f"Connected as {r.json().get('user', {}).get('displayName', 'Google user')}"

    def upload(self, path, progress, cancel):
        self._require("token")
        total = path.stat().st_size
        start = time.perf_counter()
        auth = {"Authorization": f"Bearer {self.config['token']}"}
        init = _check(requests.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable",
            headers={**auth, "Content-Type": "application/json; charset=UTF-8",
                     "X-Upload-Content-Type": "application/octet-stream",
                     "X-Upload-Content-Length": str(total)},
            json={"name": path.name}, timeout=30))
        url = init.headers["Location"]
        file_id = ""
        for offset, data, _ in self._chunks(path, self.CHUNK, cancel):
            end = offset + len(data) - 1
            rng = f"bytes {offset}-{end}/{total}" if data else f"bytes */{total}"
            r = requests.put(url, headers={**auth, "Content-Range": rng}, data=data, timeout=120)
            _check(r, (200, 201, 308))
            progress(offset + len(data), total)
            if r.status_code in (200, 201):
                file_id = r.json().get("id", "")
        return UploadResult(self.key, path.name, total, time.perf_counter() - start,
                            f"drive file {file_id}")


class OneDrive(Provider):
    key, label = "onedrive", "OneDrive"
    fields = (Field("token", "Graph access token", True),)
    help = "Needs a Microsoft Graph token with Files.ReadWrite."
    CHUNK = 32 * 320 * 1024  # must be a multiple of 320 KiB

    def test(self) -> str:
        self._require("token")
        r = _check(requests.get("https://graph.microsoft.com/v1.0/me/drive",
                                headers={"Authorization": f"Bearer {self.config['token']}"},
                                timeout=20))
        return f"Connected to {r.json().get('driveType', 'OneDrive')}"

    def upload(self, path, progress, cancel):
        self._require("token")
        total = path.stat().st_size
        start = time.perf_counter()
        session = _check(requests.post(
            f"https://graph.microsoft.com/v1.0/me/drive/root:/Quasar/{path.name}:/createUploadSession",
            headers={"Authorization": f"Bearer {self.config['token']}"},
            json={"item": {"@microsoft.graph.conflictBehavior": "rename"}}, timeout=30))
        url = session.json()["uploadUrl"]
        for offset, data, _ in self._chunks(path, self.CHUNK, cancel):
            if not data:
                break
            end = offset + len(data) - 1
            r = requests.put(url, headers={"Content-Range": f"bytes {offset}-{end}/{total}"},
                             data=data, timeout=120)
            _check(r, (200, 201, 202))
            progress(offset + len(data), total)
        return UploadResult(self.key, path.name, total, time.perf_counter() - start,
                            f"/Quasar/{path.name}")


PROVIDERS: dict[str, type[Provider]] = {
    p.key: p for p in (LocalFolder, GoogleDrive, Dropbox, OneDrive, AwsS3)
}


def make_provider(key: str, config: dict[str, str]) -> Provider:
    return PROVIDERS[key](config)
