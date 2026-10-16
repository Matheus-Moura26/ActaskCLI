import json
import os
import subprocess
from getpass import getuser

import pytest

from actask_cli.config.profiles import (
    ProfileError,
    ProfileStore,
    ServerProfile,
    derive_web_url,
)


def test_profile_store_persists_only_non_secret_active_profile(tmp_path) -> None:
    config_path = tmp_path / "profiles.json"
    first_profile = ServerProfile.create("https://actask.example.test/", "Member@Example.Test")
    active_profile = ServerProfile.create("https://other.example.test", "member@example.test")
    profiles = ProfileStore(config_path)

    profiles.save_active(first_profile)
    profiles.save_active(active_profile)

    assert profiles.active() == active_profile
    assert json.loads(config_path.read_text(encoding="utf-8")) == {
        "active": {"server_url": "https://other.example.test", "email": "member@example.test"},
        "profiles": [
            {"server_url": "https://actask.example.test", "email": "member@example.test"},
            {"server_url": "https://other.example.test", "email": "member@example.test"},
        ],
    }
    if os.name == "nt":
        permissions = subprocess.run(
            ["icacls", str(config_path)], capture_output=True, check=False, text=True
        ).stdout.lower()
        assert getuser().lower() in permissions
        assert "(f)" in permissions
    else:
        assert config_path.stat().st_mode & 0o077 == 0


def test_profile_store_persists_explicit_web_url_and_loads_legacy_profiles(tmp_path) -> None:
    config_path = tmp_path / "profiles.json"
    legacy_data = {"server_url": "https://actaskapi.bluefronte.com", "email": "a@b.test"}
    config_path.write_text(
        json.dumps({"active": legacy_data, "profiles": [legacy_data]}),
        encoding="utf-8",
    )
    profiles = ProfileStore(config_path)

    legacy = profiles.active()
    assert legacy == ServerProfile.create("https://actaskapi.bluefronte.com", "a@b.test")
    assert legacy is not None
    assert legacy.resolved_web_url == "https://actask.bluefronte.com"

    custom = ServerProfile.create(
        "https://api.example.test", "a@b.test", "https://app.example.test/"
    )
    profiles.save_active(custom)
    profiles.save_active(custom)

    assert profiles.active() == custom
    assert custom.resolved_web_url == "https://app.example.test"
    assert json.loads(config_path.read_text(encoding="utf-8"))["profiles"] == [
        {"server_url": "https://actaskapi.bluefronte.com", "email": "a@b.test"},
        {
            "server_url": "https://api.example.test",
            "email": "a@b.test",
            "web_url": "https://app.example.test",
        },
    ]


@pytest.mark.parametrize(
    ("server_url", "web_url"),
    [
        ("https://actaskapi.bluefronte.com", "https://actask.bluefronte.com"),
        ("https://actaskapistage.bluefronte.com", "https://actaskstage.bluefronte.com"),
        ("https://actaskapidev.bluefronte.com", "https://actaskdev.bluefronte.com"),
        ("https://api.example.test", None),
    ],
)
def test_profile_derives_web_url_for_official_servers(server_url: str, web_url: str | None) -> None:
    assert derive_web_url(server_url) == web_url
    assert ServerProfile.create(server_url, "a@b.test").resolved_web_url == web_url


def test_profile_requires_https_web_url() -> None:
    with pytest.raises(ProfileError, match="Web URL"):
        ServerProfile.create("https://api.example.test", "a@b.test", "http://app.example.test")


def test_profile_requires_https_url_and_email() -> None:
    with pytest.raises(ProfileError, match="HTTPS"):
        ServerProfile.create("http://actask.example.test", "member@example.test")

    with pytest.raises(ProfileError, match="email"):
        ServerProfile.create("https://actask.example.test", "  ")
