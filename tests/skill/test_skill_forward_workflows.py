"""Offline forward scenarios for the public Actask CLI Skill."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from typer.testing import CliRunner

from actask_cli.client.errors import ForbiddenError
from actask_cli.client.models import IdentityResult, Task, TaskListResult, User
from actask_cli.commands import auth, tasks
from actask_cli.config.profiles import ServerProfile
from actask_cli.main import app

PROFILE = ServerProfile.create("https://actask.example.test", "member@example.test")
USER = User("user-1", "Example User", "member@example.test", False, True, ("tasks.read",))
TASK = Task(
    "task-1",
    "EX-1",
    "Example task",
    "project-1",
    {"id": "task-1", "key": "EX-1", "title": "Example task", "project_id": "project-1"},
)
runner = CliRunner()


class FakeProfileStore:
    def active(self) -> ServerProfile:
        return PROFILE


class FakeCredentials:
    def get(self, profile: ServerProfile) -> str:
        return "<redacted-session-token>"

    def delete(self, profile: ServerProfile) -> None:
        return None


@dataclass
class IdentityClient:
    def __enter__(self) -> IdentityClient:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def whoami(self) -> IdentityResult:
        return IdentityResult(USER, "req-forward")


@dataclass
class ForbiddenTaskClient:
    def __enter__(self) -> ForbiddenTaskClient:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def list_tasks(self, payload: dict[str, object]) -> TaskListResult:
        raise ForbiddenError("req-forbidden")


def test_skill_documents_cli_only_and_required_stops() -> None:
    skill = Path("skills/actask-cli/SKILL.md").read_text(encoding="utf-8")
    reference = Path("skills/actask-cli/references/commands.md").read_text(encoding="utf-8")

    assert "Use only the installed `actask` command." in skill
    assert "Do not call the Actask API, database, browser, or credential store directly." in skill
    assert "Exit code `3` / `401`: stop." in skill
    assert "Exit code `4` / `403`: stop." in skill
    assert "--dry-run" in skill
    assert "actask whoami --json" in reference
    assert "Treat terms such as \"pendentes\"" in skill
    assert "meta.total" in skill
    assert "actask projects columns <project-id> --json" in skill
    assert "--filter column:=:<column-id>" in reference
    assert "--parent-id <parent-task-id>" in reference
    assert "assignee_name" in skill
    assert "data.assignee_name" in reference
    assert "--description-file" in skill
    assert "--description-file -" in reference
    assert "Before creating a subtask" in skill
    assert "<redacted-session-token>" not in skill + reference
    assert "https://github.com/Matheus-Moura26/ActaskCLI" in skill
    assert "SHA256SUMS" in skill
    assert "fork" in skill.lower()


def test_forward_read_identity_uses_only_a_stubbed_cli_client(monkeypatch) -> None:
    profiles = FakeProfileStore()
    credentials = FakeCredentials()
    monkeypatch.setattr(auth, "_profile_store", lambda: profiles)
    monkeypatch.setattr(auth, "_credential_store", lambda: credentials)
    monkeypatch.setattr(auth, "_client", lambda base_url, session_token=None: IdentityClient())

    result = runner.invoke(app, ["whoami", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output)["data"]["email"] == "member@example.test"


def test_forward_write_dry_run_never_creates_a_client(monkeypatch) -> None:
    def unexpected_network(*args: object, **kwargs: object) -> object:
        raise AssertionError("dry-run must not construct a network client")

    monkeypatch.setattr(tasks, "_client", unexpected_network)

    result = runner.invoke(
        app,
        [
            "tasks",
            "create",
            "--project",
            "project-1",
            "--title",
            "Safe example",
            "--sprint",
            "1",
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.output)["meta"] == {"dry_run": True}


def test_forward_forbidden_read_stops_with_backend_exit_code(monkeypatch) -> None:
    monkeypatch.setattr(tasks, "_active_session", lambda: (PROFILE, "<redacted-session-token>"))
    monkeypatch.setattr(tasks, "_client", lambda base_url, session_token: ForbiddenTaskClient())
    monkeypatch.setattr(tasks, "CredentialStore", FakeCredentials)

    result = runner.invoke(app, ["tasks", "list", "--project", "project-other", "--json"])

    assert result.exit_code == 4
    assert result.stderr == "You do not have permission to perform this action.\n"
