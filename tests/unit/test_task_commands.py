from __future__ import annotations

import json
from dataclasses import dataclass, field

from typer.testing import CliRunner

from actask_cli.client.errors import ForbiddenError
from actask_cli.client.models import Task, TaskListResult, TaskResult
from actask_cli.commands import tasks
from actask_cli.config.profiles import ServerProfile
from actask_cli.main import app

PROFILE = ServerProfile.create("https://actask.example.test", "member@example.test")
TASK = Task(
    id="task-1",
    key="EX-1",
    title="Example task",
    project_id="project-1",
    payload={
        "id": "task-1",
        "key": "EX-1",
        "title": "Example task",
        "project_id": "project-1",
    },
)
runner = CliRunner()


class FakeCredentialStore:
    def delete(self, profile: ServerProfile) -> None:
        return None


@dataclass
class FakeClient:
    payload: dict[str, object] | None = None
    foreign_project: bool = False
    foreign_task: bool = False
    payloads: list[dict[str, object]] = field(default_factory=list)

    def __enter__(self) -> FakeClient:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def list_tasks(self, payload: dict[str, object]) -> TaskListResult:
        self.payload = payload
        self.payloads.append(payload)
        if self.foreign_project:
            raise ForbiddenError("req-foreign-project")
        return TaskListResult((TASK,), 1, 2, 1, "example", (), "req-tasks")

    def show_task(self, task_id: str) -> TaskResult:
        if self.foreign_task:
            raise ForbiddenError("req-foreign-task")
        return TaskResult(TASK, "req-task")


def _install_fakes(monkeypatch, client: FakeClient) -> None:
    monkeypatch.setattr(tasks, "_active_session", lambda: (PROFILE, "<redacted-session-token>"))
    monkeypatch.setattr(tasks, "_client", lambda base_url, session_token: client)
    monkeypatch.setattr(tasks, "CredentialStore", FakeCredentialStore)


def test_tasks_list_uses_backend_filters_and_has_equivalent_json(monkeypatch) -> None:
    client = FakeClient()
    _install_fakes(monkeypatch, client)

    human = runner.invoke(
        app,
        [
            "tasks",
            "list",
            "--project",
            "project-1",
            "--page",
            "2",
            "--page-size",
            "1",
            "--query",
            "example",
            "--filter",
            "priority:equals:normal",
        ],
    )
    json_result = runner.invoke(app, ["tasks", "list", "--project", "project-1", "--json"])

    assert human.exit_code == 0
    assert human.output == "EX-1\tExample task\tproject-1\ttask-1\nPage 2 of 1 tasks.\n"
    assert client.payloads == [
        {
            "project_id": "project-1",
            "page": 2,
            "page_size": 1,
            "query": "example",
            "filters": [{"field_key": "priority", "operator": "equals", "value": "normal"}],
        },
        {"project_id": "project-1", "page": 1, "page_size": 25},
    ]
    assert json.loads(json_result.output) == {
        "data": [TASK.to_data()],
        "error": None,
        "meta": {
            "applied_order": [],
            "page": 2,
            "page_size": 1,
            "query_text": "example",
            "request_id": "req-tasks",
            "total": 1,
        },
    }


def test_tasks_list_rejects_foreign_project_with_forbidden_exit_code(monkeypatch) -> None:
    client = FakeClient(foreign_project=True)
    _install_fakes(monkeypatch, client)

    result = runner.invoke(app, ["tasks", "list", "--project", "project-foreign"])

    assert result.exit_code == 4
    assert result.stderr == "You do not have permission to perform this action.\n"


def test_tasks_show_rejects_foreign_task_with_forbidden_exit_code(monkeypatch) -> None:
    client = FakeClient(foreign_task=True)
    _install_fakes(monkeypatch, client)

    result = runner.invoke(app, ["tasks", "show", "task-foreign"])

    assert result.exit_code == 4
    assert result.stderr == "You do not have permission to perform this action.\n"


def test_tasks_list_rejects_invalid_filter_before_request(monkeypatch) -> None:
    client = FakeClient()
    _install_fakes(monkeypatch, client)

    result = runner.invoke(
        app,
        ["tasks", "list", "--project", "project-1", "--filter", "not-a-filter"],
    )

    assert result.exit_code == 2
    assert result.stderr == "Filters must use field:operator:value.\n"
    assert client.payload is None
