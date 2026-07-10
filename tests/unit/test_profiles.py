import json
import os
import subprocess
from getpass import getuser

import pytest

from actask_cli.config.profiles import ProfileError, ProfileStore, ServerProfile


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


def test_profile_requires_https_url_and_email() -> None:
    with pytest.raises(ProfileError, match="HTTPS"):
        ServerProfile.create("http://actask.example.test", "member@example.test")

    with pytest.raises(ProfileError, match="email"):
        ServerProfile.create("https://actask.example.test", "  ")
