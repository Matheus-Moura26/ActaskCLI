from __future__ import annotations

import json
from dataclasses import dataclass

from typer.testing import CliRunner

from actask_cli.client.errors import UnauthenticatedError
from actask_cli.client.models import IdentityResult, LoginResult, LogoutResult, User
from actask_cli.commands import auth
from actask_cli.config.profiles import ServerProfile
from actask_cli.main import app

SESSION_TOKEN = "<redacted-session-token>"
PROFILE = ServerProfile.create("https://actask.example.test", "member@example.test")
USER = User(
    id="user-member",
    name="Member User",
    email="member@example.test",
    is_master=False,
    is_active=True,
    permissions=("tasks.read",),
)
runner = CliRunner()


class FakeProfileStore:
    def __init__(self, active_profile: ServerProfile | None = None) -> None:
        self.active_profile = active_profile

    def active(self) -> ServerProfile | None:
        return self.active_profile

    def save_active(self, profile: ServerProfile) -> None:
        self.active_profile = profile


class FakeCredentialStore:
    def __init__(self, session_token: str | None = None) -> None:
        self.session_token = session_token

    def get(self, profile: ServerProfile) -> str | None:
        return self.session_token

    def set(self, profile: ServerProfile, session_token: str) -> None:
        self.session_token = session_token

    def delete(self, profile: ServerProfile) -> None:
        self.session_token = None


@dataclass
class FakeClient:
    login_result: LoginResult | None = None
    identity_result: IdentityResult | None = None
    logout_result: LogoutResult | None = None
    unauthenticated: bool = False
    logout_called: bool = False

    def __enter__(self) -> FakeClient:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def login(self, email: str, password: str) -> LoginResult:
        assert self.login_result is not None
        return self.login_result

    def whoami(self) -> IdentityResult:
        if self.unauthenticated:
            raise UnauthenticatedError("req-revoked")
        assert self.identity_result is not None
        return self.identity_result

    def logout(self) -> LogoutResult:
        self.logout_called = True
        if self.unauthenticated:
            raise UnauthenticatedError("req-revoked")
        assert self.logout_result is not None
        return self.logout_result


def _install_fakes(
    monkeypatch, profiles: FakeProfileStore, credentials: FakeCredentialStore, client: FakeClient
) -> None:
    monkeypatch.setattr(auth, "_profile_store", lambda: profiles)
    monkeypatch.setattr(auth, "_credential_store", lambda: credentials)
    monkeypatch.setattr(auth, "_client", lambda base_url, session_token=None: client)


def test_login_uses_default_server_and_hides_password(monkeypatch) -> None:
    profiles = FakeProfileStore()
    credentials = FakeCredentialStore()
    client = FakeClient(login_result=LoginResult(SESSION_TOKEN, USER, "req-login"))
    _install_fakes(monkeypatch, profiles, credentials, client)

    result = runner.invoke(
        app,
        ["login"],
        input="\nmember@example.test\n<redacted-password>\n",
    )

    assert result.exit_code == 0
    assert profiles.active_profile == ServerProfile.create(
        "https://actaskapi.bluefronte.com", "member@example.test"
    )
    assert credentials.session_token == SESSION_TOKEN
    assert result.output == (
        "Server URL [https://actaskapi.bluefronte.com]: \n"
        "Email: member@example.test\n"
        "Password: \n"
        "Logged in as member@example.test.\n"
    )
    assert "<redacted-password>" not in result.output
    assert "<redacted-password>" not in result.stderr
    assert SESSION_TOKEN not in result.output
    assert SESSION_TOKEN not in result.stderr


def test_whoami_has_equivalent_human_and_json_output(monkeypatch) -> None:
    profiles = FakeProfileStore(PROFILE)
    credentials = FakeCredentialStore(SESSION_TOKEN)
    client = FakeClient(identity_result=IdentityResult(USER, "req-whoami"))
    _install_fakes(monkeypatch, profiles, credentials, client)

    human = runner.invoke(app, ["whoami"])
    json_result = runner.invoke(app, ["whoami", "--json"])
    payload = json.loads(json_result.output)

    assert human.exit_code == 0
    assert json_result.exit_code == 0
    assert human.output == f"{payload['data']['name']} <{payload['data']['email']}>\n"
    assert payload["meta"] == {"request_id": "req-whoami"}
    assert payload["error"] is None


def test_whoami_json_uses_the_stable_envelope(monkeypatch) -> None:
    profiles = FakeProfileStore(PROFILE)
    credentials = FakeCredentialStore(SESSION_TOKEN)
    client = FakeClient(identity_result=IdentityResult(USER, "req-whoami"))
    _install_fakes(monkeypatch, profiles, credentials, client)

    result = runner.invoke(app, ["whoami", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "data": {
            "email": "member@example.test",
            "id": "user-member",
            "is_active": True,
            "is_master": False,
            "name": "Member User",
            "permissions": ["tasks.read"],
        },
        "error": None,
        "meta": {"request_id": "req-whoami"},
    }


def test_revoked_session_is_removed_and_can_be_replaced_by_login(monkeypatch) -> None:
    profiles = FakeProfileStore(PROFILE)
    credentials = FakeCredentialStore(SESSION_TOKEN)
    client = FakeClient(
        login_result=LoginResult(SESSION_TOKEN, USER, "req-login-after-revocation"),
        unauthenticated=True,
    )
    _install_fakes(monkeypatch, profiles, credentials, client)

    revoked_result = runner.invoke(app, ["whoami"])
    assert credentials.session_token is None
    client.unauthenticated = False
    login_result = runner.invoke(
        app,
        ["login"],
        input="https://actask.example.test\nmember@example.test\n<redacted-password>\n",
    )

    assert revoked_result.exit_code == 3
    assert revoked_result.stderr == "Session is invalid or expired. Run 'actask login'.\n"
    assert credentials.session_token == SESSION_TOKEN
    assert login_result.exit_code == 0
    assert "<redacted-password>" not in login_result.output
    assert SESSION_TOKEN not in login_result.output


def test_logout_invalidates_server_session_and_removes_credential(monkeypatch) -> None:
    profiles = FakeProfileStore(PROFILE)
    credentials = FakeCredentialStore(SESSION_TOKEN)
    client = FakeClient(logout_result=LogoutResult("req-logout"))
    _install_fakes(monkeypatch, profiles, credentials, client)

    result = runner.invoke(app, ["logout"])

    assert result.exit_code == 0
    assert client.logout_called is True
    assert credentials.session_token is None
    assert result.output == "Logged out.\n"


def test_whoami_without_session_returns_actionable_not_authenticated_error(monkeypatch) -> None:
    profiles = FakeProfileStore()
    credentials = FakeCredentialStore()
    client = FakeClient()
    _install_fakes(monkeypatch, profiles, credentials, client)

    result = runner.invoke(app, ["whoami"])

    assert result.exit_code == 3
    assert result.stderr == "No active session. Run 'actask login'.\n"
