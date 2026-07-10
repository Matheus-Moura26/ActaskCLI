"""Typed models for responses used by the Actask CLI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from actask_cli.client.errors import ServerError


@dataclass(frozen=True)
class User:
    id: str
    name: str
    email: str
    is_master: bool
    is_active: bool
    permissions: tuple[str, ...]

    @classmethod
    def from_payload(cls, payload: Mapping[str, object], request_id: str | None) -> User:
        permissions = payload.get("permissions")
        if not isinstance(permissions, list) or not all(
            isinstance(item, str) for item in permissions
        ):
            raise ServerError(request_id=request_id)
        return cls(
            id=_required_string(payload, "id", request_id),
            name=_required_string(payload, "name", request_id),
            email=_required_string(payload, "email", request_id),
            is_master=_required_boolean(payload, "is_master", request_id),
            is_active=_required_boolean(payload, "is_active", request_id),
            permissions=tuple(permissions),
        )


@dataclass(frozen=True)
class LoginResult:
    session_token: str
    user: User
    request_id: str | None


@dataclass(frozen=True)
class IdentityResult:
    user: User
    request_id: str | None


@dataclass(frozen=True)
class LogoutResult:
    request_id: str | None


@dataclass(frozen=True)
class Project:
    """A project returned by the Actask API."""

    id: str
    name: str
    key: str
    payload: Mapping[str, object]

    @classmethod
    def from_payload(cls, payload: Mapping[str, object], request_id: str | None) -> Project:
        return cls(
            id=_required_string(payload, "id", request_id),
            name=_required_string(payload, "name", request_id),
            key=_required_string(payload, "key", request_id),
            payload=dict(payload),
        )

    def to_data(self) -> dict[str, object]:
        """Return the API representation for the stable JSON output envelope."""
        return dict(self.payload)


@dataclass(frozen=True)
class ProjectListResult:
    projects: tuple[Project, ...]
    request_id: str | None


@dataclass(frozen=True)
class ProjectResult:
    project: Project
    request_id: str | None


@dataclass(frozen=True)
class Task:
    """A task returned by the Actask API."""

    id: str
    key: str
    title: str
    project_id: str
    payload: Mapping[str, object]

    @classmethod
    def from_payload(cls, payload: Mapping[str, object], request_id: str | None) -> Task:
        return cls(
            id=_required_string(payload, "id", request_id),
            key=_required_string(payload, "key", request_id),
            title=_required_string(payload, "title", request_id),
            project_id=_required_string(payload, "project_id", request_id),
            payload=dict(payload),
        )

    def to_data(self) -> dict[str, object]:
        """Return the API representation for the stable JSON output envelope."""
        return dict(self.payload)


@dataclass(frozen=True)
class TaskListResult:
    tasks: tuple[Task, ...]
    total: int
    page: int
    page_size: int
    query_text: str | None
    applied_order: tuple[object, ...]
    request_id: str | None


@dataclass(frozen=True)
class TaskResult:
    task: Task
    request_id: str | None


def _required_string(payload: Mapping[str, object], field: str, request_id: str | None) -> str:
    value = payload.get(field)
    if not isinstance(value, str):
        raise ServerError(request_id=request_id)
    return value


def _required_boolean(payload: Mapping[str, object], field: str, request_id: str | None) -> bool:
    value = payload.get(field)
    if not isinstance(value, bool):
        raise ServerError(request_id=request_id)
    return value
