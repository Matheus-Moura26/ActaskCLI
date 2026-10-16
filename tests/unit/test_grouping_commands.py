"""Tests for the public task-grouping command surface."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from typer.testing import CliRunner

from actask_cli.client.errors import NotFoundError
from actask_cli.client.models import (
    GroupedTask,
    GroupedTaskPageResult,
    Task,
    TaskGroupingCandidate,
    TaskGroupingCandidatePageResult,
    TaskGroupingOperation,
    TaskGroupingOperationPageResult,
    TaskGroupingOperationResult,
)
from actask_cli.commands import grouping
from actask_cli.config.profiles import ServerProfile
from actask_cli.main import app

PROFILE = ServerProfile.create("https://actask.example.test", "member@example.test")
USER = object()
PARENT = Task(
    "parent-1",
    "EX-1",
    "Parent task",
    "project-1",
    {
        "id": "parent-1",
        "key": "EX-1",
        "title": "Parent task",
        "project_id": "project-1",
    },
)
CHILD = Task(
    "child-1",
    "EX-2",
    "Child task",
    "project-1",
    {
        "id": "child-1",
        "key": "EX-2",
        "title": "Child task",
        "project_id": "project-1",
    },
)
OPERATION_PAYLOAD = {
    "id": "operation-1",
    "project_id": "project-1",
    "parent_task_id": "parent-1",
    "parent_task_key_snapshot": "EX-1",
    "parent_task_title_snapshot": "Parent task",
    "status": "active",
    "item_count": 1,
    "can_undo": True,
    "items": [],
}
OPERATION = TaskGroupingOperation(
    "operation-1",
    "active",
    "project-1",
    OPERATION_PAYLOAD,
)
CANDIDATE = TaskGroupingCandidate(
    "child-1",
    "EX-2",
    "Child task",
    "project-1",
    {
        "id": "child-1",
        "key": "EX-2",
        "title": "Child task",
        "project_id": "project-1",
        "can_be_parent": True,
        "can_be_child": True,
        "is_grouping_task": False,
        "is_grouped_task": False,
        "grouped_task_count": 0,
    },
)
PARENT_CANDIDATE = TaskGroupingCandidate(
    "parent-1",
    "EX-1",
    "Parent task",
    "project-1",
    {
        "id": "parent-1",
        "key": "EX-1",
        "title": "Parent task",
        "project_id": "project-1",
        "can_be_parent": True,
        "can_be_child": True,
        "is_grouping_task": False,
        "is_grouped_task": False,
        "grouped_task_count": 0,
    },
)
GROUPED = GroupedTask(
    "child-1",
    "EX-2",
    "Child task",
    "project-1",
    {
        **CHILD.payload,
        "grouping_parent_id": "parent-1",
        "is_grouping_task": False,
        "is_grouped_task": True,
        "grouped_task_count": 0,
    },
)
runner = CliRunner()


class FakeCredentialStore:
    def delete(self, profile: ServerProfile) -> None:
        return None


@dataclass
class FakeClient:
    payload: dict[str, object] | None = None
    candidate_args: tuple[object, ...] | None = None
    shown_task_ids: list[str] = field(default_factory=list)
    undo_args: tuple[str, str] | None = None

    def __enter__(self) -> FakeClient:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def show_task(self, task_id: str):
        self.shown_task_ids.append(task_id)
        if task_id == PARENT.id:
            return type("TaskResult", (), {"task": PARENT})()
        if task_id == CHILD.id:
            return type("TaskResult", (), {"task": CHILD})()
        raise AssertionError(f"unexpected task ID: {task_id}")

    def create_task_grouping(self, project_id: str, payload: dict[str, object]):
        self.payload = payload
        return TaskGroupingOperationResult(OPERATION, "req-group")

    def list_task_grouping_candidates(
        self,
        project_id: str,
        *,
        query: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ):
        self.candidate_args = (project_id, query, page, page_size)
        return TaskGroupingCandidatePageResult(
            (CANDIDATE,), page, page_size, False, None, "req-candidates"
        )

    def list_task_groupings(
        self,
        project_id: str,
        *,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ):
        return TaskGroupingOperationPageResult(
            (OPERATION,), page, page_size, False, None, "req-log"
        )

    def list_grouped_tasks(self, parent_task_id: str, *, page: int = 1, page_size: int = 100):
        return GroupedTaskPageResult((GROUPED,), page, page_size, False, None, "req-children")

    def undo_task_grouping(self, project_id: str, operation_id: str):
        self.undo_args = (project_id, operation_id)
        return TaskGroupingOperationResult(
            TaskGroupingOperation(
                OPERATION.id,
                "undone",
                OPERATION.project_id,
                {**OPERATION.payload, "status": "undone", "can_undo": False},
            ),
            "req-undo",
        )


@dataclass
class KeyReferenceClient(FakeClient):
    def show_task(self, task_id: str):
        if task_id in {"EX-1", "EX-2"}:
            raise NotFoundError("req-key-lookup")
        return super().show_task(task_id)

    def list_task_grouping_candidates(
        self,
        project_id: str,
        *,
        query: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ):
        self.candidate_args = (project_id, query, page, page_size)
        return TaskGroupingCandidatePageResult(
            (PARENT_CANDIDATE, CANDIDATE), page, page_size, False, None, "req-candidates"
        )


def _install_fakes(monkeypatch, client: FakeClient) -> None:
    monkeypatch.setattr(grouping, "_active_session", lambda: (PROFILE, "<redacted-session-token>"))
    monkeypatch.setattr(grouping, "_client", lambda base_url, session_token: client)
    monkeypatch.setattr(grouping, "CredentialStore", FakeCredentialStore)


def test_group_dry_run_normalizes_payload_without_network(monkeypatch) -> None:
    def unexpected_network(*args: object, **kwargs: object) -> object:
        raise AssertionError("dry-run must not construct a network client")

    monkeypatch.setattr(grouping, "_client", unexpected_network)

    result = runner.invoke(
        app,
        [
            "tasks",
            "grouping",
            "group",
            "--project",
            "project-1",
            "--parent",
            "parent-1",
            "--child",
            "child-1",
            "--idempotency-key",
            "batch-1",
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "data": {
            "idempotency_key": "batch-1",
            "parent_task_id": "parent-1",
            "project_id": "project-1",
            "task_ids": ["child-1"],
        },
        "error": None,
        "meta": {"dry_run": True},
    }


def test_group_reads_targets_and_posts_one_authorized_batch(monkeypatch) -> None:
    client = FakeClient()
    _install_fakes(monkeypatch, client)

    result = runner.invoke(
        app,
        [
            "tasks",
            "grouping",
            "group",
            "--project",
            "project-1",
            "--parent",
            "parent-1",
            "--child",
            "child-1",
            "--yes",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert client.shown_task_ids == ["parent-1", "child-1"]
    assert client.payload == {
        "parent_task_id": "parent-1",
        "task_ids": ["child-1"],
    }
    assert json.loads(result.output)["data"] == OPERATION_PAYLOAD


def test_group_rejects_duplicate_or_parent_child_before_network(monkeypatch) -> None:
    def unexpected_network(*args: object, **kwargs: object) -> object:
        raise AssertionError("invalid input must not construct a network client")

    monkeypatch.setattr(grouping, "_client", unexpected_network)

    result = runner.invoke(
        app,
        [
            "tasks",
            "grouping",
            "group",
            "--project",
            "project-1",
            "--parent",
            "parent-1",
            "--child",
            "child-1",
            "--child",
            "child-1",
        ],
    )

    assert result.exit_code == 2
    assert result.stderr == "The same child task ID cannot be repeated.\n"


def test_group_accepts_web_urls_and_detects_url_id_duplicates(monkeypatch) -> None:
    def unexpected_network(*args: object, **kwargs: object) -> object:
        raise AssertionError("dry-run and invalid input must not construct a network client")

    monkeypatch.setattr(grouping, "_client", unexpected_network)
    base = "https://actask.bluefronte.com/tasks/all?task="
    command = ["tasks", "grouping", "group", "--project", "project-1"]

    dry_run = runner.invoke(
        app,
        [
            *command,
            "--parent",
            f"{base}parent-1",
            "--child",
            f"{base}child-1",
            "--dry-run",
            "--json",
        ],
    )
    duplicate = runner.invoke(
        app,
        [*command, "--parent", "parent-1", "--child", f"{base}parent-1"],
    )

    assert dry_run.exit_code == 0
    assert json.loads(dry_run.output)["data"]["parent_task_id"] == "parent-1"
    assert json.loads(dry_run.output)["data"]["task_ids"] == ["child-1"]
    assert duplicate.exit_code == 2
    assert duplicate.stderr == "The parent task cannot also be a child task.\n"


def test_children_accepts_parent_web_url(monkeypatch) -> None:
    client = FakeClient()
    _install_fakes(monkeypatch, client)
    parents: list[str] = []
    original = client.list_grouped_tasks

    def recorder(parent_task_id: str, *, page: int = 1, page_size: int = 100):
        parents.append(parent_task_id)
        return original(parent_task_id, page=page, page_size=page_size)

    monkeypatch.setattr(client, "list_grouped_tasks", recorder)

    result = runner.invoke(
        app,
        [
            "tasks",
            "grouping",
            "children",
            "https://actask.bluefronte.com/tasks/all?task=parent-1",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert parents == ["parent-1"]


def test_group_resolves_exact_public_keys_before_posting_ids(monkeypatch) -> None:
    client = KeyReferenceClient()
    _install_fakes(monkeypatch, client)

    result = runner.invoke(
        app,
        [
            "tasks",
            "grouping",
            "group",
            "--project",
            "project-1",
            "--parent",
            "EX-1",
            "--child",
            "EX-2",
            "--yes",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert client.payload == {
        "parent_task_id": "parent-1",
        "task_ids": ["child-1"],
    }
    assert client.candidate_args == ("project-1", None, 1, 100)


def test_candidates_log_and_children_have_json_pagination(monkeypatch) -> None:
    client = FakeClient()
    _install_fakes(monkeypatch, client)

    candidates = runner.invoke(
        app,
        [
            "tasks",
            "grouping",
            "candidates",
            "--project",
            "project-1",
            "--query",
            "child",
            "--page",
            "2",
            "--page-size",
            "25",
            "--json",
        ],
    )
    log = runner.invoke(
        app,
        ["tasks", "grouping", "log", "--project", "project-1", "--json"],
    )
    children = runner.invoke(
        app,
        ["tasks", "grouping", "children", "parent-1", "--json"],
    )

    assert candidates.exit_code == log.exit_code == children.exit_code == 0
    assert client.candidate_args == ("project-1", "child", 2, 25)
    assert json.loads(candidates.output)["data"] == [CANDIDATE.to_data()]
    assert json.loads(log.output)["data"] == [OPERATION_PAYLOAD]
    assert json.loads(children.output)["data"] == [GROUPED.to_data()]


def test_undo_reads_log_then_posts_operation(monkeypatch) -> None:
    client = FakeClient()
    _install_fakes(monkeypatch, client)

    result = runner.invoke(
        app,
        [
            "tasks",
            "grouping",
            "undo",
            "--project",
            "project-1",
            "--operation-id",
            "operation-1",
            "--yes",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert client.undo_args == ("project-1", "operation-1")
    assert json.loads(result.output)["data"]["status"] == "undone"
