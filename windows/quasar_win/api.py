"""Client for the Quasar backend (see backend/ and docs/API.md)."""
from __future__ import annotations

from typing import Any

import requests


class ApiError(Exception):
    pass


class QuasarApi:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = ""
        self.user: dict[str, Any] = {}

    @property
    def logged_in(self) -> bool:
        return bool(self.token)

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = kwargs.pop("headers", {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            r = requests.request(method, self.base_url + path, headers=headers, timeout=15, **kwargs)
        except requests.RequestException as exc:
            raise ApiError(f"Cannot reach the Quasar server at {self.base_url}") from exc
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except ValueError:
                detail = r.text
            raise ApiError(str(detail)[:300])
        return r.json() if r.content else None

    def register(self, email: str, password: str, full_name: str) -> dict:
        return self._request("POST", "/auth/register",
                             json={"email": email, "password": password, "full_name": full_name})

    def login(self, email: str, password: str) -> dict:
        data = self._request("POST", "/auth/token", data={"username": email, "password": password})
        self.token = data["access_token"]
        self.user = data.get("user", {})
        return self.user

    def logout(self) -> None:
        self.token, self.user = "", {}

    def providers(self) -> list[dict]:
        return self._request("GET", "/backups/providers")["providers"]

    def sessions(self) -> list[dict]:
        return self._request("GET", "/backups/sessions")

    def create_session(self, provider: str, device_name: str, file_path: str = "") -> dict:
        return self._request("POST", "/backups/sessions", json={
            "provider": provider, "device_name": device_name,
            "encrypted_file_path": file_path or None, "backup_status": "queued"})

    def profile_link(self) -> dict:
        try:
            return self._request("GET", "/backups/profile-link")
        except ApiError:
            return self._request("POST", "/backups/profile-link")
