"""Non-secret server profile persistence."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from getpass import getuser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

DEFAULT_SERVER_URL = "https://actaskapi.bluefronte.com"


class ProfileError(ValueError):
    """Raised when a server profile cannot be safely used."""


@dataclass(frozen=True)
class ServerProfile:
    """The non-secret server and user reference for one Actask session."""

    server_url: str
    email: str
    web_url: str | None = None

    @classmethod
    def create(cls, server_url: str, email: str, web_url: str | None = None) -> ServerProfile:
        normalized_email = email.strip().lower()
        if not normalized_email:
            raise ProfileError("An email address is required.")
        normalized_web_url = (
            normalize_web_url(web_url) if web_url is not None and web_url.strip() else None
        )
        return cls(
            server_url=normalize_server_url(server_url),
            email=normalized_email,
            web_url=normalized_web_url,
        )

    @property
    def resolved_web_url(self) -> str | None:
        """Return the web app URL used for task links, when it is known."""

        return self.web_url or derive_web_url(self.server_url)

    def to_data(self) -> dict[str, str]:
        data = {"server_url": self.server_url, "email": self.email}
        if self.web_url is not None:
            data["web_url"] = self.web_url
        return data


def normalize_server_url(server_url: str) -> str:
    """Return a canonical HTTPS API base URL."""

    parsed = urlsplit(server_url.strip())
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        raise ProfileError("Server URL must be an HTTPS URL without query parameters.")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


def normalize_web_url(web_url: str) -> str:
    """Return a canonical HTTPS web app base URL."""

    parsed = urlsplit(web_url.strip())
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        raise ProfileError("Web URL must be an HTTPS URL without query parameters.")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


def derive_web_url(server_url: str) -> str | None:
    """Derive the web app URL of the official Actask deployments from their API URL.

    ``actaskapi.<domain>`` serves ``actask.<domain>`` and ``actaskapi<env>.<domain>``
    serves ``actask<env>.<domain>``. Other servers return ``None``.
    """

    host = urlsplit(server_url).hostname
    if host is None or "." not in host:
        return None
    first_label, domain = host.split(".", 1)
    if not first_label.startswith("actaskapi"):
        return None
    return f"https://actask{first_label.removeprefix('actaskapi')}.{domain}"


class ProfileStore:
    """Persist non-secret profiles for the current operating-system user."""

    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path

    @classmethod
    def default(cls) -> ProfileStore:
        return cls(Path.home() / ".actask" / "profiles.json")

    def save_active(self, profile: ServerProfile) -> None:
        profiles = self._profiles()
        profiles = [
            item
            for item in profiles
            if (item.server_url, item.email) != (profile.server_url, profile.email)
        ]
        profiles.append(profile)
        self._write(
            {"active": profile.to_data(), "profiles": [item.to_data() for item in profiles]}
        )

    def active(self) -> ServerProfile | None:
        if not self._config_path.exists():
            return None
        try:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
            active = data.get("active")
            if active is None:
                return None
            return ServerProfile.create(
                active["server_url"], active["email"], active.get("web_url")
            )
        except (AttributeError, KeyError, TypeError, json.JSONDecodeError) as error:
            raise ProfileError("Actask profile configuration is invalid.") from error

    def _profiles(self) -> list[ServerProfile]:
        if not self._config_path.exists():
            return []
        try:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
            return [
                ServerProfile.create(item["server_url"], item["email"], item.get("web_url"))
                for item in data["profiles"]
            ]
        except (AttributeError, KeyError, TypeError, json.JSONDecodeError) as error:
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
