from __future__ import annotations

import json
from dataclasses import dataclass, field

from typer.testing import CliRunner

from actask_cli.client.errors import ConflictError, ForbiddenError
from actask_cli.client.models import (
    Case,
    CaseResult,
    Comment,
    CommentListResult,
    CommentResult,
    IdentityResult,
    ProjectCatalogResult,
    Task,
    TaskListResult,
    TaskResult,
    User,
)
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
        "assignee_name": None,
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

CASE = Case(
    id="case-1",
    payload={
        "id": "case-1",
        "description": "Case description",
        "tenant_id": "tenant-1",
        "person_ids": ["person-1"],
        "is_done": False,
        "motivo": "Broken",
        "solucao": None,
        "field_values": [],
    },
)

COMMENT = Comment(
    id="comment-1",
    payload={
        "id": "comment-1",
        "user_id": "user-1",
        "author_name": "Member User",
        "content": "Please review @Ana",
        "parent_id": None,
        "created_at": "2026-08-11T12:00:00Z",
    },
)

CASE_FIELDS = (
    {
        "id": "field-text",
        "label": "Summary",
        "field_type": "text",
        "is_active": True,
        "options": [],
    },
    {
        "id": "field-number",
        "label": "Count",
        "field_type": "number",
        "is_active": True,
        "options": [],
    },
    {
        "id": "field-select",
        "label": "State",
        "field_type": "select_single",
        "is_active": True,
        "options": [{"value": "open", "label": "Open"}],
    },
    {
        "id": "field-multi",
        "label": "Tags",
        "field_type": "select_multi",
        "is_active": True,
        "options": [
            {"value": "a", "label": "A"},
            {"value": "b", "label": "B"},
        ],
    },
)


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
    task_assignee_name: str | None = None
    payloads: list[dict[str, object]] = field(default_factory=list)
    case_payloads: list[dict[str, object]] | None = None
    case_fields: tuple[dict[str, object], ...] = CASE_FIELDS
    created_case: Case | None = None
    updated_case: Case | None = None
    created_comment: Comment | None = None

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
        payload = {
            **TASK.payload,
            "assignee_id": self.task_assignee_id,
            "assignee_name": self.task_assignee_name,
        }
        if self.case_payloads is not None:
            payload["cases"] = self.case_payloads
        task = Task(
            id=TASK.id,
            key=TASK.key,
            title=TASK.title,
            project_id=TASK.project_id,
            payload=payload,
        )
        return TaskResult(task, "req-task")

    def whoami(self) -> IdentityResult:
        return IdentityResult(CURRENT_USER, "req-identity")

    def list_project_case_fields(self, project_id: str) -> ProjectCatalogResult:
        return ProjectCatalogResult(tuple(self.case_fields), "req-case-fields")

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

    def list_comments(self, task_id: str) -> CommentListResult:
        return CommentListResult((COMMENT,), "req-comments")

    def create_comment(self, task_id: str, payload: dict[str, object]) -> CommentResult:
        self.payload = payload
        self.created_comment = COMMENT
        return CommentResult(COMMENT, "req-comment-create")

    def move_task(self, task_id: str, column_id: str, position: int | None = None) -> TaskResult:
        self.payload = {"column_id": column_id, "position": position}
        self.payloads.append(self.payload)
        if self.conflict:
            raise ConflictError("req-conflict")
        return TaskResult(TASK, "req-move")

    def create_case(self, task_id: str, payload: dict[str, object]) -> CaseResult:
        self.payload = payload
        self.created_case = CASE
        return CaseResult(CASE, "req-case-create")

    def update_case(
        self,
        task_id: str,
        case_id: str,
        payload: dict[str, object],
    ) -> CaseResult:
        self.payload = payload
        self.updated_case = CASE
        return CaseResult(CASE, "req-case-update")


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
    assert human.output == "EX-1\tExample task\tproject-1\ttask-1\t\nPage 2 of 1 tasks.\n"
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


def test_task_assignee_name_accepts_nested_summary_payload() -> None:
    task = Task(
        id="task-1",
        key="EX-1",
        title="Example task",
        project_id="project-1",
        payload={
            "id": "task-1",
            "key": "EX-1",
            "title": "Example task",
            "project_id": "project-1",
            "assignee": {"id": "user-2", "name": "Other User"},
        },
    )

    assert task.assignee_name == "Other User"


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
        f"\t{payload['data']['project_id']}\t{payload['data']['id']}"
        f"\t{payload['data']['assignee_name'] or ''}\n"
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
    assert result.output == "EX-1\tExample task\tproject-1\ttask-1\t\n"


def test_tasks_create_reads_multiline_description_file(tmp_path) -> None:
    description_file = tmp_path / "description.md"
    description_file.write_text("Context\n\nAcceptance criteria\n", encoding="utf-8")

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
            "--description-file",
            str(description_file),
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.output)["data"]["description"] == (
        "Context\n\nAcceptance criteria\n"
    )


def test_tasks_create_reads_multiline_description_from_stdin() -> None:
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
            "--description-file",
            "-",
            "--dry-run",
            "--json",
        ],
        input="Context\n\nAcceptance criteria\n",
    )

    assert result.exit_code == 0
    assert json.loads(result.output)["data"]["description"] == (
        "Context\n\nAcceptance criteria\n"
    )


def test_tasks_create_rejects_description_options_used_together(tmp_path) -> None:
    description_file = tmp_path / "description.md"
    description_file.write_text("From file", encoding="utf-8")

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
            "--description",
            "Inline",
            "--description-file",
            str(description_file),
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 2
    assert result.stderr == "Use either --description or --description-file, not both.\n"


def test_tasks_show_includes_assignee_name_in_human_output(monkeypatch) -> None:
    client = FakeClient(task_assignee_id="user-2", task_assignee_name="Other User")
    _install_fakes(monkeypatch, client)

    result = runner.invoke(app, ["tasks", "show", "task-1"])

    assert result.exit_code == 0
    assert result.output == "EX-1\tExample task\tproject-1\ttask-1\tOther User\n"


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


def test_tasks_update_reads_multiline_description_file(tmp_path) -> None:
    description_file = tmp_path / "updated-description.md"
    description_file.write_text("Updated context\nSecond line\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "tasks",
            "update",
            "task-1",
            "--description-file",
            str(description_file),
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.output)["data"] == {
        "description": "Updated context\nSecond line\n",
    }


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
def test_tasks_cases_list_exposes_case_ids_and_json_payload(monkeypatch) -> None:
    client = FakeClient(case_payloads=[CASE.to_data()])
    _install_fakes(monkeypatch, client)

    human = runner.invoke(app, ["tasks", "cases", "list", "task-1"])
    json_result = runner.invoke(app, ["tasks", "cases", "list", "task-1", "--json"])

    assert human.exit_code == 0
    assert human.output == "case-1\topen\tBroken\n1 cases.\n"
    assert json.loads(json_result.output) == {
        "data": [CASE.to_data()],
        "error": None,
        "meta": {"request_id": "req-task", "task_id": "task-1", "total": 1},
    }


def test_tasks_comments_list_exposes_comment_ids_and_json_payload(monkeypatch) -> None:
    client = FakeClient()
    _install_fakes(monkeypatch, client)

    human = runner.invoke(app, ["tasks", "comments", "list", "task-1"])
    json_result = runner.invoke(app, ["tasks", "comments", "list", "task-1", "--json"])

    assert human.exit_code == 0
    assert human.output == "comment-1\tMember User\tPlease review @Ana\n1 comments.\n"
    assert json.loads(json_result.output) == {
        "data": [COMMENT.to_data()],
        "error": None,
        "meta": {"request_id": "req-comments", "task_id": "task-1", "total": 1},
    }


def test_tasks_comments_create_dry_run_includes_mentions_and_parent(monkeypatch) -> None:
    def unexpected_network(*args: object, **kwargs: object) -> object:
        raise AssertionError("dry-run must not construct a network client")

    monkeypatch.setattr(tasks, "_client", unexpected_network)

    result = runner.invoke(
        app,
        [
            "tasks",
            "comments",
            "create",
            "task-1",
            "--content",
            "Please review @Ana",
            "--mention-user-id",
            "user-2",
            "--mention-user-id",
            "user-3",
            "--parent-id",
            "comment-0",
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "data": {
            "content": "Please review @Ana",
            "mentioned_user_ids": ["user-2", "user-3"],
            "parent_id": "comment-0",
        },
        "error": None,
        "meta": {"dry_run": True},
    }


def test_tasks_comments_create_sends_mentions_after_responsibility_guard(monkeypatch) -> None:
    client = FakeClient()
    _install_fakes(monkeypatch, client)

    result = runner.invoke(
        app,
        [
            "tasks",
            "comments",
            "create",
            "task-1",
            "--content",
            "Please review @Ana",
            "--mention-user-id",
            "user-2",
            "--yes",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert client.payload == {
        "content": "Please review @Ana",
        "mentioned_user_ids": ["user-2"],
    }
    assert json.loads(result.output) == {
        "data": COMMENT.to_data(),
        "error": None,
        "meta": {"request_id": "req-comment-create"},
    }


def test_tasks_comments_create_rejects_other_assignee_before_writing(monkeypatch) -> None:
    client = FakeClient(task_assignee_id="user-2")
    _install_fakes(monkeypatch, client)

    result = runner.invoke(
        app,
        [
            "tasks",
            "comments",
            "create",
            "task-1",
            "--content",
            "Please review",
            "--yes",
        ],
    )

    assert result.exit_code == 4
    assert result.stderr == "Você não é o responsável desta task\n"
    assert client.payload is None
    assert client.created_comment is None


def test_tasks_cases_fields_lists_project_definitions(monkeypatch) -> None:
    client = FakeClient()
    _install_fakes(monkeypatch, client)

    result = runner.invoke(app, ["tasks", "cases", "fields", "task-1", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "data": list(CASE_FIELDS),
        "error": None,
        "meta": {
            "project_id": "project-1",
            "request_id": "req-case-fields",
            "task_id": "task-1",
        },
    }


def test_tasks_cases_create_validates_fields_and_sends_payload(monkeypatch) -> None:
    client = FakeClient()
    _install_fakes(monkeypatch, client)

    result = runner.invoke(
        app,
        [
            "tasks",
            "cases",
            "create",
            "task-1",
            "--description",
            "New case",
            "--tenant-id",
            "tenant-2",
            "--person-id",
            "person-2",
            "--field-values",
            '{"field-text":"hello","field-number":3,"field-select":"open","field-multi":["a","b"]}',
            "--yes",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert client.payload == {
        "description": "New case",
        "tenant_id": "tenant-2",
        "person_ids": ["person-2"],
        "field_values": {
            "field-text": "hello",
            "field-number": 3,
            "field-select": "open",
            "field-multi": ["a", "b"],
        },
    }
    assert json.loads(result.output) == {
        "data": CASE.to_data(),
        "error": None,
        "meta": {"request_id": "req-case-create"},
    }


def test_tasks_cases_create_dry_run_does_not_connect(monkeypatch) -> None:
    def unexpected_network(*args: object, **kwargs: object) -> object:
        raise AssertionError("dry-run must not construct a network client")

    monkeypatch.setattr(tasks, "_client", unexpected_network)

    result = runner.invoke(
        app,
        [
            "tasks",
            "cases",
            "create",
            "task-1",
            "--field-values",
            '{"field-text":"hello"}',
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "data": {
            "description": "",
            "person_ids": [],
            "field_values": {"field-text": "hello"},
        },
        "error": None,
        "meta": {"dry_run": True},
    }


def test_tasks_cases_create_reads_description_file(tmp_path) -> None:
    description_file = tmp_path / "case-description.md"
    description_file.write_text("Case context\n\nSteps\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "tasks",
            "cases",
            "create",
            "task-1",
            "--description-file",
            str(description_file),
            "--field-values",
            '{"field-text":"hello"}',
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.output)["data"]["description"] == "Case context\n\nSteps\n"


def test_tasks_cases_create_rejects_invalid_option_before_writing(monkeypatch) -> None:
    client = FakeClient()
    _install_fakes(monkeypatch, client)

    result = runner.invoke(
        app,
        [
            "tasks",
            "cases",
            "create",
            "task-1",
            "--field-values",
            '{"field-select":"closed"}',
            "--yes",
        ],
    )

    assert result.exit_code == 2
    assert result.stderr == "Case field 'field-select' expects one of the configured options.\n"
    assert client.created_case is None


def test_tasks_cases_update_sends_native_and_custom_fields(monkeypatch) -> None:
    client = FakeClient()
    _install_fakes(monkeypatch, client)

    result = runner.invoke(
        app,
        [
            "tasks",
            "cases",
            "update",
            "task-1",
            "case-1",
            "--description",
            "Updated case",
            "--clear-person-ids",
            "--is-done",
            "false",
            "--field-values",
            '{"field-number":4}',
            "--yes",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert client.payload == {
        "description": "Updated case",
        "person_ids": [],
        "is_done": False,
        "field_values": {"field-number": 4},
    }
    assert json.loads(result.output)["meta"] == {"request_id": "req-case-update"}


def test_tasks_cases_update_rejects_other_assignee_before_writing(monkeypatch) -> None:
    client = FakeClient(task_assignee_id="user-2")
    _install_fakes(monkeypatch, client)

    result = runner.invoke(
        app,
        ["tasks", "cases", "update", "task-1", "case-1", "--description", "Updated", "--yes"],
    )

    assert result.exit_code == 4
    assert result.stderr == "Você não é o responsável desta task\n"
    assert client.payload is None
