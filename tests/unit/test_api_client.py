import json

import httpx
import pytest

from actask_cli.client.api import ActaskApiClient
from actask_cli.client.errors import (
    ConflictError,
    ExitCode,
    ForbiddenError,
    InvalidInputError,
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
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    client = ActaskApiClient(BASE_URL, transport=httpx.MockTransport(handler))

    with pytest.raises(NetworkError) as error:
        client.whoami()

    assert error.value.exit_code == ExitCode.NETWORK_OR_SERVER
    assert error.value.status_code is None


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
        ("GET", "/projects/project-1"),
    ]
    assert all(request.headers["X-Session-Token"] == SESSION_TOKEN for request in requests)
