from __future__ import annotations

import json
from dataclasses import dataclass, field

from typer.testing import CliRunner

from actask_cli.client.errors import ConflictError, ForbiddenError
from actask_cli.client.models import IdentityResult, Task, TaskListResult, TaskResult, User
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
        "assignee_id": None,
    },
)
CURRENT_USER = User(
    id="user-1",
    name="Member User",
    email="member@example.test",
    is_master=False,
    is_active=True,
    permissions=("tasks.read",),
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
    conflict: bool = False
    task_assignee_id: str | None = None
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
        task = Task(
            id=TASK.id,
            key=TASK.key,
            title=TASK.title,
            project_id=TASK.project_id,
            payload={**TASK.payload, "assignee_id": self.task_assignee_id},
        )
        return TaskResult(task, "req-task")

    def whoami(self) -> IdentityResult:
        return IdentityResult(CURRENT_USER, "req-identity")

    def create_task(self, payload: dict[str, object]) -> TaskResult:
        self.payload = payload
        if self.foreign_project:
            raise ForbiddenError("req-foreign-project")
        return TaskResult(TASK, "req-create")

    def update_task(self, task_id: str, payload: dict[str, object]) -> TaskResult:
        self.payload = payload
        self.payloads.append(payload)
        if self.conflict:
            raise ConflictError("req-conflict")
        return TaskResult(TASK, "req-update")

    def move_task(self, task_id: str, column_id: str, position: int | None = None) -> TaskResult:
        self.payload = {"column_id": column_id, "position": position}
        self.payloads.append(self.payload)
        if self.conflict:
            raise ConflictError("req-conflict")
        return TaskResult(TASK, "req-move")


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


def test_tasks_show_has_equivalent_human_and_json_output(monkeypatch) -> None:
    client = FakeClient()
    _install_fakes(monkeypatch, client)

    human = runner.invoke(app, ["tasks", "show", "task-1"])
    json_result = runner.invoke(app, ["tasks", "show", "task-1", "--json"])
    payload = json.loads(json_result.output)

    assert human.exit_code == 0
    assert json_result.exit_code == 0
    assert human.output == (
        f"{payload['data']['key']}\t{payload['data']['title']}"
        f"\t{payload['data']['project_id']}\t{payload['data']['id']}\n"
    )
    assert payload == {
        "data": TASK.to_data(),
        "error": None,
        "meta": {"request_id": "req-task"},
    }


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


def test_tasks_create_sends_normalized_payload_after_confirmation(monkeypatch) -> None:
    client = FakeClient()
    _install_fakes(monkeypatch, client)

    result = runner.invoke(
        app,
        [
            "tasks",
            "create",
            "--project",
            "project-1",
            "--title",
            "Example",
            "--sprint",
            "1",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    assert client.payload == {
        "project_id": "project-1",
        "title": "Example",
        "sprint": 1,
        "description": "",
        "priority": "normal",
        "type": "task",
    }
    assert result.output == "EX-1\tExample task\tproject-1\ttask-1\n"


def test_tasks_create_rejects_invalid_input_without_request(monkeypatch) -> None:
    client = FakeClient()
    _install_fakes(monkeypatch, client)

    result = runner.invoke(
        app,
        ["tasks", "create", "--project", "project-1", "--title", "   ", "--sprint", "1", "--yes"],
    )

    assert result.exit_code == 2
    assert result.stderr == "A task title is required.\n"
    assert client.payload is None


def test_tasks_create_subtask_sends_parent_id_after_confirmation(monkeypatch) -> None:
    client = FakeClient()
    _install_fakes(monkeypatch, client)

    result = runner.invoke(
        app,
        [
            "tasks",
            "create",
            "--project",
            "project-1",
            "--title",
            "Example subtask",
            "--sprint",
            "1",
            "--parent-id",
            "task-parent",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    assert client.payload == {
        "project_id": "project-1",
        "title": "Example subtask",
        "sprint": 1,
        "description": "",
        "priority": "normal",
        "type": "task",
        "parent_id": "task-parent",
    }


def test_tasks_create_rejects_empty_parent_id_without_request(monkeypatch) -> None:
    client = FakeClient()
    _install_fakes(monkeypatch, client)

    result = runner.invoke(
        app,
        [
            "tasks",
            "create",
            "--project",
            "project-1",
            "--title",
            "Example subtask",
            "--sprint",
            "1",
            "--parent-id",
            "   ",
            "--yes",
        ],
    )

    assert result.exit_code == 2
    assert result.stderr == "A parent task ID cannot be empty.\n"
    assert client.payload is None


def test_tasks_create_preserves_forbidden_response(monkeypatch) -> None:
    client = FakeClient(foreign_project=True)
    _install_fakes(monkeypatch, client)

    result = runner.invoke(
        app,
        [
            "tasks",
            "create",
            "--project",
            "project-foreign",
            "--title",
            "Example",
            "--sprint",
            "1",
            "--yes",
        ],
    )

    assert result.exit_code == 4
    assert result.stderr == "You do not have permission to perform this action.\n"


def test_tasks_update_preserves_conflict_response(monkeypatch) -> None:
    client = FakeClient(conflict=True)
    _install_fakes(monkeypatch, client)

    result = runner.invoke(app, ["tasks", "update", "task-1", "--title", "Updated", "--yes"])

    assert result.exit_code == 6
    assert result.stderr == "Request conflicts with current Actask state.\n"


def test_tasks_update_allows_an_unassigned_task(monkeypatch) -> None:
    client = FakeClient()
    _install_fakes(monkeypatch, client)

    result = runner.invoke(app, ["tasks", "update", "task-1", "--title", "Updated", "--yes"])

    assert result.exit_code == 0
    assert client.payloads == [{"title": "Updated"}]


def test_tasks_update_allows_task_assigned_to_current_user(monkeypatch) -> None:
    client = FakeClient(task_assignee_id=CURRENT_USER.id)
    _install_fakes(monkeypatch, client)

    result = runner.invoke(app, ["tasks", "update", "task-1", "--title", "Updated", "--yes"])

    assert result.exit_code == 0
    assert client.payloads == [{"title": "Updated"}]


def test_tasks_update_rejects_task_assigned_to_another_user_before_writing(monkeypatch) -> None:
    client = FakeClient(task_assignee_id="user-2")
    _install_fakes(monkeypatch, client)

    result = runner.invoke(app, ["tasks", "update", "task-1", "--title", "Updated", "--yes"])

    assert result.exit_code == 4
    assert result.stderr == "Você não é o responsável desta task\n"
    assert client.payloads == []


def test_tasks_move_rejects_task_assigned_to_another_user_before_writing(monkeypatch) -> None:
    client = FakeClient(task_assignee_id="user-2")
    _install_fakes(monkeypatch, client)

    result = runner.invoke(
        app,
        ["tasks", "update", "task-1", "--column-id", "column-2", "--yes"],
    )

    assert result.exit_code == 4
    assert result.stderr == "Você não é o responsável desta task\n"
    assert client.payloads == []


def test_tasks_update_cancellation_does_not_mutate(monkeypatch) -> None:
    client = FakeClient()
    _install_fakes(monkeypatch, client)

    result = runner.invoke(app, ["tasks", "update", "task-1", "--title", "Updated"], input="n\n")

    assert result.exit_code == 0
    assert result.output == "Update this task? [y/N]: n\nCancelled.\n"
    assert client.payload is None


def test_tasks_create_dry_run_does_not_connect_and_shows_normalized_json(monkeypatch) -> None:
    client = FakeClient()
    _install_fakes(monkeypatch, client)

    result = runner.invoke(
        app,
        [
            "tasks",
            "create",
            "--project",
            "project-1",
            "--title",
            "Example",
            "--sprint",
            "1",
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "data": {
            "project_id": "project-1",
            "title": "Example",
            "sprint": 1,
            "description": "",
            "priority": "normal",
            "type": "task",
        },
        "error": None,
        "meta": {"dry_run": True},
    }
    assert client.payload is None


def test_tasks_update_dry_run_does_not_create_a_client_and_shows_normalized_json(
    monkeypatch,
) -> None:
    def unexpected_network(*args: object, **kwargs: object) -> object:
        raise AssertionError("dry-run must not construct a network client")

    monkeypatch.setattr(tasks, "_client", unexpected_network)

    result = runner.invoke(
        app,
        [
            "tasks",
            "update",
            "task-1",
            "--column-id",
            "column-2",
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "data": {
            "move": {"column_id": "column-2"},
        },
        "error": None,
        "meta": {"dry_run": True},
    }


def test_tasks_update_moves_column_with_canonical_route(monkeypatch) -> None:
    client = FakeClient()
    _install_fakes(monkeypatch, client)

    result = runner.invoke(
        app,
        ["tasks", "update", "task-1", "--column-id", "column-2", "--yes", "--json"],
    )

    assert result.exit_code == 0
    assert client.payloads == [{"column_id": "column-2", "position": None}]
    assert json.loads(result.output)["meta"] == {"request_id": "req-move"}


def test_tasks_update_passes_explicit_position_to_move(monkeypatch) -> None:
    client = FakeClient()
    _install_fakes(monkeypatch, client)

    result = runner.invoke(
        app,
        [
            "tasks",
            "update",
            "task-1",
            "--column-id",
            "column-2",
            "--position",
            "0",
            "--yes",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert client.payloads == [{"column_id": "column-2", "position": 0}]


def test_tasks_update_rejects_position_without_column(monkeypatch) -> None:
    client = FakeClient()
    _install_fakes(monkeypatch, client)

    result = runner.invoke(app, ["tasks", "update", "task-1", "--position", "0", "--yes"])

    assert result.exit_code == 2
    assert result.stderr == "--position requires --column-id.\n"
    assert client.payload is None


def test_tasks_update_rejects_move_combined_with_other_fields_before_request(monkeypatch) -> None:
    client = FakeClient()
    _install_fakes(monkeypatch, client)

    result = runner.invoke(
        app,
        [
            "tasks",
            "update",
            "task-1",
            "--column-id",
            "column-2",
            "--title",
            "Updated",
            "--yes",
        ],
    )

    assert result.exit_code == 2
    assert result.stderr == (
        "--column-id cannot be combined with other task fields; "
        "move the task in a separate command.\n"
    )
    assert client.payload is None
