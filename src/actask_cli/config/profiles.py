"""Non-secret server profile persistence."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import asdict, dataclass
from getpass import getuser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


class ProfileError(ValueError):
    """Raised when a server profile cannot be safely used."""


@dataclass(frozen=True)
class ServerProfile:
    """The non-secret server and user reference for one Actask session."""

    server_url: str
    email: str

    @classmethod
    def create(cls, server_url: str, email: str) -> ServerProfile:
        normalized_email = email.strip().lower()
        if not normalized_email:
            raise ProfileError("An email address is required.")
        return cls(server_url=normalize_server_url(server_url), email=normalized_email)


def normalize_server_url(server_url: str) -> str:
    """Return a canonical HTTPS API base URL."""

    parsed = urlsplit(server_url.strip())
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        raise ProfileError("Server URL must be an HTTPS URL without query parameters.")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


class ProfileStore:
    """Persist non-secret profiles for the current operating-system user."""

    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path

    @classmethod
    def default(cls) -> ProfileStore:
        return cls(Path.home() / ".actask" / "profiles.json")

    def save_active(self, profile: ServerProfile) -> None:
        profiles = self._profiles()
        profiles = [item for item in profiles if item != profile]
        profiles.append(profile)
        self._write({"active": asdict(profile), "profiles": [asdict(item) for item in profiles]})

    def active(self) -> ServerProfile | None:
        if not self._config_path.exists():
            return None
        try:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
            active = data.get("active")
            if active is None:
                return None
            return ServerProfile.create(active["server_url"], active["email"])
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise ProfileError("Actask profile configuration is invalid.") from error

    def _profiles(self) -> list[ServerProfile]:
        if not self._config_path.exists():
            return []
        try:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
            return [
                ServerProfile.create(item["server_url"], item["email"])
                for item in data["profiles"]
            ]
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise ProfileError("Actask profile configuration is invalid.") from error

    def _write(self, data: dict[str, object]) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        _restrict_permissions(self._config_path)


def _restrict_permissions(path: Path) -> None:
    if os.name != "nt":
        os.chmod(path, 0o600)
        return
    result = subprocess.run(
        ["icacls", str(path), "/inheritance:r", "/grant:r", f"{getuser()}:(F)"],
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise ProfileError("Actask profile configuration could not be secured.")
