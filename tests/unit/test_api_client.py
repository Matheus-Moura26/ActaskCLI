import json

import httpx
import pytest

from actask_cli.client.api import ActaskApiClient
from actask_cli.client.errors import (
    ConflictError,
    ExitCode,
    ForbiddenError,
    InvalidInputError,
    MethodNotAllowedError,
    NetworkError,
    NotFoundError,
    ServerError,
    UnauthenticatedError,
)

BASE_URL = "https://actask.example.test"
SESSION_TOKEN = "<redacted-session-token>"
USER = {
    "id": "user-member",
    "name": "Member User",
    "email": "member@example.test",
    "is_master": False,
    "is_active": True,
    "permissions": ["tasks.read"],
}
PROJECT = {"id": "project-1", "name": "Example Project", "key": "EX"}
TASK = {"id": "task-1", "key": "EX-1", "title": "Example task", "project_id": "project-1"}


def test_client_sends_login_body_and_typed_authenticated_requests() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        headers = {"X-Request-ID": "req-123"}
        if request.url.path == "/auth/login":
            return httpx.Response(
                200, headers=headers, json={"session_token": SESSION_TOKEN, "user": USER}
            )
        if request.url.path == "/auth/me":
            return httpx.Response(200, headers=headers, json=USER)
        return httpx.Response(200, headers=headers, json={"detail": "logged out"})

    transport = httpx.MockTransport(handler)
    with ActaskApiClient(BASE_URL, transport=transport) as client:
        login = client.login("member@example.test", "<redacted-password>")
    with ActaskApiClient(BASE_URL, session_token=SESSION_TOKEN, transport=transport) as client:
        identity = client.whoami()
        logout = client.logout()

    assert login.session_token == SESSION_TOKEN
    assert login.user.email == "member@example.test"
    assert login.request_id == "req-123"
    assert identity.user.permissions == ("tasks.read",)
    assert identity.request_id == "req-123"
    assert logout.request_id == "req-123"
    assert json.loads(requests[0].content) == {
        "email": "member@example.test",
        "password": "<redacted-password>",
    }
    assert requests[0].headers.get("X-Session-Token") is None
    assert requests[1].headers.get("X-Session-Token") == SESSION_TOKEN
    assert requests[2].headers.get("X-Session-Token") == SESSION_TOKEN
    assert all(request.url.query == b"" for request in requests)
    assert [(request.method, request.url.path) for request in requests] == [
        ("POST", "/auth/login"),
        ("GET", "/auth/me"),
        ("POST", "/auth/logout"),
    ]


@pytest.mark.parametrize(
    ("status_code", "error_type", "exit_code"),
    [
        (400, InvalidInputError, ExitCode.INVALID_INPUT),
        (401, UnauthenticatedError, ExitCode.NOT_AUTHENTICATED),
        (403, ForbiddenError, ExitCode.FORBIDDEN),
        (404, NotFoundError, ExitCode.NOT_FOUND),
        (409, ConflictError, ExitCode.CONFLICT),
        (405, MethodNotAllowedError, ExitCode.NETWORK_OR_SERVER),
        (422, InvalidInputError, ExitCode.INVALID_INPUT),
        (500, ServerError, ExitCode.NETWORK_OR_SERVER),
    ],
)
def test_client_maps_http_errors_to_stable_exit_codes(status_code, error_type, exit_code) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code, headers={"X-Request-ID": "req-error"}, json={"detail": "error"}
        )

    client = ActaskApiClient(BASE_URL, transport=httpx.MockTransport(handler))

    with pytest.raises(error_type) as error:
        client.whoami()

    assert error.value.exit_code == exit_code
    assert error.value.status_code == status_code
    assert error.value.request_id == "req-error"


def test_client_maps_timeout_to_network_error() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        raise httpx.ReadTimeout("timed out", request=request)

    client = ActaskApiClient(BASE_URL, transport=httpx.MockTransport(handler))

    with pytest.raises(NetworkError) as error:
        client.whoami()

    assert error.value.exit_code == ExitCode.NETWORK_OR_SERVER
    assert error.value.status_code is None
    assert error.value.method == "GET"
    assert error.value.path == "/auth/me"
    assert error.value.cause_type == "ReadTimeout"
    assert "GET /auth/me" in str(error.value)
    assert "ReadTimeout" in str(error.value)
    assert SESSION_TOKEN not in str(error.value)
    assert len(requests) == 1


def test_client_rejects_non_https_server_url() -> None:
    with pytest.raises(InvalidInputError) as error:
        ActaskApiClient("http://actask.example.test")

    assert error.value.exit_code == ExitCode.INVALID_INPUT


def test_client_reads_projects_from_the_authorized_routes() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/projects":
            return httpx.Response(200, headers={"X-Request-ID": "req-list"}, json=[PROJECT])
        return httpx.Response(200, headers={"X-Request-ID": "req-show"}, json=PROJECT)

    with ActaskApiClient(
        BASE_URL, session_token=SESSION_TOKEN, transport=httpx.MockTransport(handler)
    ) as client:
        listed = client.list_projects()
        shown = client.show_project("project-1")

    assert [project.to_data() for project in listed.projects] == [PROJECT]
    assert listed.request_id == "req-list"
    assert shown.project.to_data() == PROJECT
    assert shown.request_id == "req-show"
    assert [(request.method, request.url.path) for request in requests] == [
        ("GET", "/projects"),
        ("GET", "/task-loading/v1/projects/project-1"),
    ]
    assert all(request.headers["X-Session-Token"] == SESSION_TOKEN for request in requests)


def test_client_reads_project_columns_and_field_registry() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/projects/project-1/columns":
            return httpx.Response(200, json=[{"id": "column-pending", "name": "Pendentes"}])
        return httpx.Response(200, json=[{"key": "status", "options": []}])

    with ActaskApiClient(
        BASE_URL, session_token=SESSION_TOKEN, transport=httpx.MockTransport(handler)
    ) as client:
        columns = client.list_project_columns("project-1")
        fields = client.list_project_field_registry("project-1")

    assert columns.entries == ({"id": "column-pending", "name": "Pendentes"},)
    assert fields.entries == ({"key": "status", "options": []},)
    assert [request.url.path for request in requests] == [
        "/projects/project-1/columns",
        "/projects/project-1/task-fields/registry",
    ]


def test_client_reads_tasks_from_the_authorized_routes() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/tasks/query":
            return httpx.Response(
                200,
                headers={"X-Request-ID": "req-list"},
                json={
                    "items": [TASK],
                    "total": 1,
                    "page": 1,
                    "page_size": 25,
                    "query_text": None,
                    "applied_order": [],
                },
            )
        return httpx.Response(200, headers={"X-Request-ID": "req-show"}, json=TASK)

    with ActaskApiClient(
        BASE_URL, session_token=SESSION_TOKEN, transport=httpx.MockTransport(handler)
    ) as client:
        listed = client.list_tasks({"project_id": "project-1", "page": 1, "page_size": 25})
        shown = client.show_task("task-1")

    assert [task.to_data() for task in listed.tasks] == [TASK]
    assert (listed.total, listed.page, listed.page_size) == (1, 1, 25)
    assert shown.task.to_data() == TASK
    assert [(request.method, request.url.path) for request in requests] == [
        ("POST", "/tasks/query"),
        ("GET", "/tasks/task-1"),
    ]
    assert json.loads(requests[0].content) == {
        "project_id": "project-1",
        "page": 1,
        "page_size": 25,
    }


def test_client_writes_tasks_to_the_authorized_routes() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, headers={"X-Request-ID": "req-write"}, json=TASK)

    with ActaskApiClient(
        BASE_URL, session_token=SESSION_TOKEN, transport=httpx.MockTransport(handler)
    ) as client:
        created = client.create_task({"project_id": "project-1", "title": "Example", "sprint": 1})
        updated = client.update_task("task-1", {"title": "Updated"})

    assert created.task.to_data() == TASK
    assert updated.task.to_data() == TASK
    assert [(request.method, request.url.path) for request in requests] == [
        ("POST", "/tasks"),
        ("PUT", "/tasks/task-1"),
    ]
    assert json.loads(requests[0].content) == {
        "project_id": "project-1",
        "title": "Example",
        "sprint": 1,
    }
    assert json.loads(requests[1].content) == {"title": "Updated"}


@pytest.mark.parametrize(
    ("position", "expected_placement"),
    [
        (None, {"append_to_end": True}),
        (0, {"position": 0}),
        (1, {"position": 1}),
    ],
)
def test_client_moves_task_with_ordering_revisions_without_project_prefetch(
    position: int | None,
    expected_placement: dict[str, object],
) -> None:
    moving_task = {
        **TASK,
        "column_id": "column-1",
        "position": 0,
        "created_at": "2026-08-03T10:00:00Z",
        "is_archived": False,
    }
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/tasks/task-1":
            return httpx.Response(200, json=moving_task)
        if request.url.path == "/projects/project-1/columns":
            return httpx.Response(
                200,
                json=[
                    {"id": "column-1", "ordering_revision": 4},
                    {"id": "column-2", "ordering_revision": 9},
                ],
            )
        if request.url.path == "/tasks/query":
            raise AssertionError("move must not query project tasks")
        if request.url.path == "/tasks/task-1/move":
            return httpx.Response(200, json={**moving_task, "column_id": "column-2"})
        raise AssertionError(f"unexpected request path: {request.url.path}")

    with ActaskApiClient(
        BASE_URL, session_token=SESSION_TOKEN, transport=httpx.MockTransport(handler)
    ) as client:
        moved = client.move_task("task-1", "column-2", position)

    assert moved.task.to_data()["column_id"] == "column-2"
    assert [(request.method, request.url.path) for request in requests] == [
        ("GET", "/tasks/task-1"),
        ("GET", "/projects/project-1/columns"),
        ("PATCH", "/tasks/task-1/move"),
    ]
    expected_payload = {
        "column_id": "column-2",
        "expected_source_column_id": "column-1",
        "expected_source_ordering_revision": 4,
        "expected_target_ordering_revision": 9,
    }
    expected_payload.update(expected_placement)
    assert json.loads(requests[-1].content) == expected_payload


def test_client_reorders_within_column_without_anchoring_to_the_moving_task() -> None:
    moving_task = {
        **TASK,
        "column_id": "column-2",
        "position": 1,
        "created_at": "2026-08-03T10:01:00Z",
        "is_archived": False,
    }
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/tasks/task-1":
            return httpx.Response(200, json=moving_task)
        if request.url.path == "/projects/project-1/columns":
            return httpx.Response(
                200,
                json=[
                    {"id": "column-1", "ordering_revision": 4},
                    {"id": "column-2", "ordering_revision": 9},
                ],
            )
        if request.url.path == "/tasks/query":
            raise AssertionError("move must not query project tasks")
        if request.url.path == "/tasks/task-1/move":
            return httpx.Response(200, json={**moving_task, "position": 0})
        raise AssertionError(f"unexpected request path: {request.url.path}")

    with ActaskApiClient(
        BASE_URL, session_token=SESSION_TOKEN, transport=httpx.MockTransport(handler)
    ) as client:
        client.move_task("task-1", "column-2", position=0)

    assert json.loads(requests[-1].content) == {
        "column_id": "column-2",
        "expected_source_column_id": "column-2",
        "expected_source_ordering_revision": 9,
        "expected_target_ordering_revision": 9,
        "position": 0,
    }
