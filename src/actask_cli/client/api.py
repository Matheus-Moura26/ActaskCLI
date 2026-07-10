"""HTTPX client for the Actask API contract."""

from __future__ import annotations

from typing import Mapping, Self
from urllib.parse import urlsplit

import httpx

from actask_cli.client.errors import (
    ApiError,
    ConflictError,
    ForbiddenError,
    InvalidInputError,
    NetworkError,
    NotFoundError,
    ServerError,
    UnauthenticatedError,
)
from actask_cli.client.models import (
    IdentityResult,
    LoginResult,
    LogoutResult,
    Project,
    ProjectListResult,
    ProjectResult,
    Task,
    TaskListResult,
    TaskResult,
    User,
)


class ActaskApiClient:
    """Call the HTTPS Actask API without exposing session credentials."""

    def __init__(
        self,
        base_url: str,
        session_token: str | None = None,
        *,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        parsed = urlsplit(base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise InvalidInputError(400, None)
        headers = {"Accept": "application/json"}
        if session_token is not None:
            headers["X-Session-Token"] = session_token
        self._client = httpx.Client(
            base_url=base_url.rstrip("/") + "/",
            headers=headers,
            timeout=timeout,
            transport=transport,
            verify=True,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def login(self, email: str, password: str) -> LoginResult:
        response = self._request(
            "POST", "auth/login", json_body={"email": email, "password": password}
        )
        payload = _payload(response)
        request_id = _request_id(response)
        return LoginResult(
            session_token=_required_session_token(payload, request_id),
            user=User.from_payload(_required_object(payload, "user", request_id), request_id),
            request_id=request_id,
        )

    def whoami(self) -> IdentityResult:
        response = self._request("GET", "auth/me")
        request_id = _request_id(response)
        return IdentityResult(
            user=User.from_payload(_payload(response), request_id),
            request_id=request_id,
        )

    def logout(self) -> LogoutResult:
        response = self._request("POST", "auth/logout")
        return LogoutResult(request_id=_request_id(response))

    def list_projects(self) -> ProjectListResult:
        response = self._request("GET", "projects")
        request_id = _request_id(response)
        payload = _payload_list(response)
        return ProjectListResult(
            projects=tuple(
                Project.from_payload(_required_mapping(item, request_id), request_id)
                for item in payload
            ),
            request_id=request_id,
        )

    def show_project(self, project_id: str) -> ProjectResult:
        response = self._request("GET", f"projects/{project_id}")
        request_id = _request_id(response)
        return ProjectResult(
            project=Project.from_payload(_payload(response), request_id),
            request_id=request_id,
        )

    def list_tasks(self, payload: Mapping[str, object]) -> TaskListResult:
        response = self._request("POST", "tasks/query", json_body=payload)
        request_id = _request_id(response)
        body = _payload(response)
        items = body.get("items")
        if not isinstance(items, list):
            raise ServerError(request_id=request_id)
        return TaskListResult(
            tasks=tuple(
                Task.from_payload(_required_mapping(item, request_id), request_id)
                for item in items
            ),
            total=_required_integer(body, "total", request_id),
            page=_required_integer(body, "page", request_id),
            page_size=_required_integer(body, "page_size", request_id),
            query_text=_optional_string(body, "query_text", request_id),
            applied_order=_required_list(body, "applied_order", request_id),
            request_id=request_id,
        )

    def show_task(self, task_id: str) -> TaskResult:
        response = self._request("GET", f"tasks/{task_id}")
        request_id = _request_id(response)
        return TaskResult(
            task=Task.from_payload(_payload(response), request_id),
            request_id=request_id,
        )

    def create_task(self, payload: Mapping[str, object]) -> TaskResult:
        response = self._request("POST", "tasks", json_body=payload)
        request_id = _request_id(response)
        return TaskResult(
            task=Task.from_payload(_payload(response), request_id),
            request_id=request_id,
        )

    def update_task(self, task_id: str, payload: Mapping[str, object]) -> TaskResult:
        response = self._request("PUT", f"tasks/{task_id}", json_body=payload)
        request_id = _request_id(response)
        return TaskResult(
            task=Task.from_payload(_payload(response), request_id),
            request_id=request_id,
        )

    def _request(
        self, method: str, path: str, json_body: Mapping[str, object] | None = None
    ) -> httpx.Response:
        try:
            response = self._client.request(method, path, json=json_body)
        except httpx.RequestError as error:
            raise NetworkError() from error
        if response.is_error:
            raise _response_error(response)
        return response


def _request_id(response: httpx.Response) -> str | None:
    request_id = response.headers.get("X-Request-ID")
    return request_id if isinstance(request_id, str) else None


def _response_error(response: httpx.Response) -> ApiError:
    request_id = _request_id(response)
    if response.status_code in (400, 422):
        return InvalidInputError(response.status_code, request_id)
    if response.status_code == 401:
        return UnauthenticatedError(request_id)
    if response.status_code == 403:
        return ForbiddenError(request_id)
    if response.status_code == 404:
        return NotFoundError(request_id)
    if response.status_code == 409:
        return ConflictError(request_id)
    return ServerError(response.status_code, request_id)


def _payload(response: httpx.Response) -> dict[str, object]:
    request_id = _request_id(response)
    try:
        payload: object = response.json()
    except ValueError as error:
        raise ServerError(response.status_code, request_id) from error
    if not isinstance(payload, dict):
        raise ServerError(response.status_code, request_id)
    return payload


def _payload_list(response: httpx.Response) -> list[object]:
    request_id = _request_id(response)
    try:
        payload: object = response.json()
    except ValueError as error:
        raise ServerError(response.status_code, request_id) from error
    if not isinstance(payload, list):
        raise ServerError(response.status_code, request_id)
    return payload


def _required_object(
    payload: dict[str, object], field: str, request_id: str | None
) -> dict[str, object]:
    value = payload.get(field)
    if not isinstance(value, dict):
        raise ServerError(request_id=request_id)
    return value


def _required_mapping(value: object, request_id: str | None) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ServerError(request_id=request_id)
    return value


def _required_integer(payload: Mapping[str, object], field: str, request_id: str | None) -> int:
    value = payload.get(field)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ServerError(request_id=request_id)
    return value


def _optional_string(
    payload: Mapping[str, object], field: str, request_id: str | None
) -> str | None:
    value = payload.get(field)
    if value is not None and not isinstance(value, str):
        raise ServerError(request_id=request_id)
    return value


def _required_list(
    payload: Mapping[str, object], field: str, request_id: str | None
) -> tuple[object, ...]:
    value = payload.get(field)
    if not isinstance(value, list):
        raise ServerError(request_id=request_id)
    return tuple(value)


def _required_session_token(payload: dict[str, object], request_id: str | None) -> str:
    value = payload.get("session_token")
    if not isinstance(value, str) or not value:
        raise ServerError(request_id=request_id)
    return value
