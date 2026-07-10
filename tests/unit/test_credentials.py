import pytest
from keyring.errors import KeyringError

from actask_cli.config.credentials import CredentialStore, CredentialStoreError
from actask_cli.config.profiles import ProfileStore, ServerProfile


class FakeKeyring:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def get_password(self, service_name: str, username: str) -> str | None:
        return self.values.get((service_name, username))

    def set_password(self, service_name: str, username: str, password: str) -> None:
        self.values[(service_name, username)] = password

    def delete_password(self, service_name: str, username: str) -> None:
        self.values.pop((service_name, username))


class FailingKeyring(FakeKeyring):
    def set_password(self, service_name: str, username: str, password: str) -> None:
        raise KeyringError(f"unable to store {password}")


def test_credentials_are_isolated_by_server_and_user() -> None:
    keyring = FakeKeyring()
    credentials = CredentialStore(keyring)
    primary = ServerProfile.create("https://actask.example.test", "member@example.test")
    other_user = ServerProfile.create("https://actask.example.test", "other@example.test")
    other_server = ServerProfile.create("https://other.example.test", "member@example.test")

    credentials.set(primary, "<redacted-session-token>")

    assert credentials.get(primary) == "<redacted-session-token>"
    assert credentials.get(other_user) is None
    assert credentials.get(other_server) is None


def test_session_token_is_not_written_to_profile_configuration(tmp_path) -> None:
    config_path = tmp_path / "profiles.json"
    profile = ServerProfile.create("https://actask.example.test", "member@example.test")
    session_token = "<redacted-session-token>"
    ProfileStore(config_path).save_active(profile)

    CredentialStore(FakeKeyring()).set(profile, session_token)

    assert session_token not in config_path.read_text(encoding="utf-8")


def test_keyring_errors_do_not_expose_session_token() -> None:
    credentials = CredentialStore(FailingKeyring())
    profile = ServerProfile.create("https://actask.example.test", "member@example.test")
    session_token = "<redacted-session-token>"

    with pytest.raises(CredentialStoreError) as error:
        credentials.set(profile, session_token)

    assert str(error.value) == "Secure credential store is unavailable."
    assert session_token not in str(error.value)
