"""Public task-grouping commands backed by the authorized Actask API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import NoReturn

import typer

from actask_cli.client.api import ActaskApiClient
from actask_cli.client.errors import ApiError, ExitCode, NotFoundError, UnauthenticatedError
from actask_cli.client.models import (
    GroupedTaskPageResult,
    Task,
    TaskGroupingCandidate,
    TaskGroupingCandidatePageResult,
    TaskGroupingOperation,
    TaskGroupingOperationPageResult,
)
from actask_cli.commands.auth import _active_session, _client, _delete_after_unauthenticated
from actask_cli.commands.projects import _write_json
from actask_cli.config.credentials import CredentialStore

app = typer.Typer(
    help="Group root tasks under one visible parent task and manage the grouping log."
)


@app.command("candidates")
def list_candidates(
    project_id: str = typer.Option(..., "--project", help="Project ID to query."),
    page: int = typer.Option(1, min=1, help="Page number."),
    page_size: int = typer.Option(100, min=1, help="Number of candidates per page."),
    query: str | None = typer.Option(None, "--query", help="Search by task key or title."),
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON envelope."),
) -> None:
    """List active root tasks and their grouping eligibility."""

    normalized_project_id = _require_non_empty(project_id, "A project ID is required.")
    profile, session_token = _active_session()
    credentials = CredentialStore()
    try:
        with _client(profile.server_url, session_token) as client:
            result = client.list_task_grouping_candidates(
                normalized_project_id,
                query=query,
                page=page,
                page_size=page_size,
            )
    except UnauthenticatedError as error:
        _delete_after_unauthenticated(credentials, profile)
        _exit_api_error(error)
    except ApiError as error:
        _exit_api_error(error)

    meta = _page_meta(result, result.request_id)
    if json_output:
        _write_json([candidate.to_data() for candidate in result.candidates], meta)
        return
    _write_candidate_list(result)


@app.command("group")
def group_tasks(
    project_id: str = typer.Option(..., "--project", help="Project ID containing every task."),
    parent_task_id: str = typer.Option(
        ..., "--parent", help="Existing root task that remains visible on the board."
    ),
    child_ids: list[str] = typer.Option(
        [],
        "--child",
        help="Existing root task ID to hide under the parent; repeat for every task.",
    ),
    idempotency_key: str | None = typer.Option(
        None,
        "--idempotency-key",
        "--request-id",
        help="Optional key for safely retrying the same grouping batch.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show the normalized payload only."),
    yes: bool = typer.Option(False, "--yes", help="Confirm the change without a prompt."),
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON envelope."),
) -> None:
    """Group one or more existing root tasks under an existing parent task."""

    _group_tasks(
        project_id,
        parent_task_id,
        child_ids,
        idempotency_key,
        dry_run,
        yes,
        json_output,
    )


@app.command("create")
def create_grouping(
    project_id: str = typer.Option(..., "--project", help="Project ID containing every task."),
    parent_task_id: str = typer.Option(
        ..., "--parent", help="Existing root task that remains visible on the board."
    ),
    child_ids: list[str] = typer.Option(
        [],
        "--child",
        help="Existing root task ID to hide under the parent; repeat for every task.",
    ),
    idempotency_key: str | None = typer.Option(
        None,
        "--idempotency-key",
        "--request-id",
        help="Optional key for safely retrying the same grouping batch.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show the normalized payload only."),
    yes: bool = typer.Option(False, "--yes", help="Confirm the change without a prompt."),
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON envelope."),
) -> None:
    """Alias for ``group`` using the API resource naming."""

    _group_tasks(
        project_id,
        parent_task_id,
        child_ids,
        idempotency_key,
        dry_run,
        yes,
        json_output,
    )


@app.command("list")
def list_groupings(
    project_id: str = typer.Option(..., "--project", help="Project ID to query."),
    status: str | None = typer.Option(
        None,
        "--status",
        help="Filter the audit log by active or undone.",
    ),
    page: int = typer.Option(1, min=1, help="Page number."),
    page_size: int = typer.Option(50, min=1, help="Number of operations per page."),
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON envelope."),
) -> None:
    """List the newest grouping operations for a project."""

    _list_groupings(project_id, status, page, page_size, json_output)


@app.command("log")
def log_groupings(
    project_id: str = typer.Option(..., "--project", help="Project ID to query."),
    status: str | None = typer.Option(
        None,
        "--status",
        help="Filter the audit log by active or undone.",
    ),
    page: int = typer.Option(1, min=1, help="Page number."),
    page_size: int = typer.Option(50, min=1, help="Number of operations per page."),
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON envelope."),
) -> None:
    """Alias for ``list`` using the audit-log naming."""

    _list_groupings(project_id, status, page, page_size, json_output)


@app.command("children")
def list_grouped_children(
    parent_task_id: str,
    page: int = typer.Option(1, min=1, help="Page number."),
    page_size: int = typer.Option(100, min=1, help="Number of grouped tasks per page."),
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON envelope."),
) -> None:
    """List tasks hidden in a grouping parent's Agrupadas section."""

    normalized_parent_id = _require_non_empty(parent_task_id, "A parent task ID is required.")
    profile, session_token = _active_session()
    credentials = CredentialStore()
    try:
        with _client(profile.server_url, session_token) as client:
            result = client.list_grouped_tasks(
                normalized_parent_id,
                page=page,
                page_size=page_size,
            )
    except UnauthenticatedError as error:
        _delete_after_unauthenticated(credentials, profile)
        _exit_api_error(error)
    except ApiError as error:
        _exit_api_error(error)

    meta = _page_meta(result, result.request_id)
    if json_output:
        _write_json([task.to_data() for task in result.tasks], meta)
        return
    _write_grouped_task_list(result)


@app.command("undo")
def undo_grouping(
    project_id: str = typer.Option(..., "--project", help="Project containing the operation."),
    operation_id: str = typer.Option(..., "--operation-id", help="Grouping operation ID."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show the normalized payload only."),
    yes: bool = typer.Option(False, "--yes", help="Confirm the change without a prompt."),
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON envelope."),
) -> None:
    """Undo every active relationship recorded by one grouping operation."""

    normalized_project_id = _require_non_empty(project_id, "A project ID is required.")
    normalized_operation_id = _require_non_empty(operation_id, "An operation ID is required.")
    payload: dict[str, object] = {
        "project_id": normalized_project_id,
        "operation_id": normalized_operation_id,
    }
    if dry_run:
        _write_dry_run(payload, json_output)
        return

    profile, session_token = _active_session()
    credentials = CredentialStore()
    try:
        with _client(profile.server_url, session_token) as client:
            operation = _find_operation(client, normalized_project_id, normalized_operation_id)
            status = _payload_string(operation.payload, "status") or "unknown"
            if not _confirm(
                f"Undo grouping operation {normalized_operation_id} ({status})?",
                yes,
            ):
                _write_cancelled(json_output)
                return
            result = client.undo_task_grouping(
                normalized_project_id,
                normalized_operation_id,
            )
    except UnauthenticatedError as error:
        _delete_after_unauthenticated(credentials, profile)
        _exit_api_error(error)
    except ApiError as error:
        _exit_api_error(error)

    _write_operation_result(result.operation, result.request_id, json_output)


def _group_tasks(
    project_id: str,
    parent_task_id: str,
    child_ids: list[str],
    idempotency_key: str | None,
    dry_run: bool,
    yes: bool,
    json_output: bool,
) -> None:
    payload = _grouping_payload(project_id, parent_task_id, child_ids, idempotency_key)
    if dry_run:
        _write_dry_run(payload, json_output)
        return

    profile, session_token = _active_session()
    credentials = CredentialStore()
    try:
        with _client(profile.server_url, session_token) as client:
            project_value = payload["project_id"]
            parent_value = payload["parent_task_id"]
            task_ids_value = payload["task_ids"]
            assert isinstance(project_value, str)
            assert isinstance(parent_value, str)
            assert isinstance(task_ids_value, list)
            parent, children, resolved_parent_id, resolved_child_ids = _read_grouping_targets(
                client,
                project_value,
                parent_value,
                [str(task_id) for task_id in task_ids_value],
            )
            if not _confirm(
                f"Group {len(children)} task(s) under {parent.key} ({parent.id})?",
                yes,
            ):
                _write_cancelled(json_output)
                return
            request_payload = {
                key: value for key, value in payload.items() if key != "project_id"
            }
            request_payload["parent_task_id"] = resolved_parent_id
            request_payload["task_ids"] = resolved_child_ids
            result = client.create_task_grouping(project_value, request_payload)
    except UnauthenticatedError as error:
        _delete_after_unauthenticated(credentials, profile)
        _exit_api_error(error)
    except ApiError as error:
        _exit_api_error(error)

    _write_operation_result(result.operation, result.request_id, json_output)


def _list_groupings(
    project_id: str,
    status: str | None,
    page: int,
    page_size: int,
    json_output: bool,
) -> None:
    normalized_project_id = _require_non_empty(project_id, "A project ID is required.")
    normalized_status = _normalize_status(status)
    profile, session_token = _active_session()
    credentials = CredentialStore()
    try:
        with _client(profile.server_url, session_token) as client:
            result = client.list_task_groupings(
                normalized_project_id,
                status=normalized_status,
                page=page,
                page_size=page_size,
            )
    except UnauthenticatedError as error:
        _delete_after_unauthenticated(credentials, profile)
        _exit_api_error(error)
    except ApiError as error:
        _exit_api_error(error)

    meta = _page_meta(result, result.request_id)
    if json_output:
        _write_json([operation.to_data() for operation in result.operations], meta)
        return
    _write_operation_list(result)


def _grouping_payload(
    project_id: str,
    parent_task_id: str,
    child_ids: list[str],
    idempotency_key: str | None,
) -> dict[str, object]:
    normalized_project_id = _require_non_empty(project_id, "A project ID is required.")
    normalized_parent_id = _require_non_empty(parent_task_id, "A parent task ID is required.")
    if not child_ids:
        _exit("Provide at least one --child task ID.", ExitCode.INVALID_INPUT)

    normalized_child_ids = [
        _require_non_empty(child_id, "A child task ID cannot be empty.") for child_id in child_ids
    ]
    if len(normalized_child_ids) != len(set(normalized_child_ids)):
        _exit("The same child task ID cannot be repeated.", ExitCode.INVALID_INPUT)
    if normalized_parent_id in normalized_child_ids:
        _exit("The parent task cannot also be a child task.", ExitCode.INVALID_INPUT)

    payload: dict[str, object] = {
        "project_id": normalized_project_id,
        "parent_task_id": normalized_parent_id,
        "task_ids": normalized_child_ids,
    }
    if idempotency_key is not None:
        normalized_key = _require_non_empty(
            idempotency_key,
            "An idempotency key cannot be empty.",
        )
        if len(normalized_key) > 255:
            _exit("An idempotency key cannot exceed 255 characters.", ExitCode.INVALID_INPUT)
        payload["idempotency_key"] = normalized_key
    return payload


def _read_grouping_targets(
    client: ActaskApiClient,
    project_id: str,
    parent_reference: str,
    child_references: list[str],
) -> tuple[Task, tuple[Task, ...], str, list[str]]:
    parent_task_id, child_ids, tasks_by_id = _resolve_task_references(
        client,
        project_id,
        parent_reference,
        child_references,
    )
    if parent_task_id in child_ids:
        _exit("The parent task cannot also be a child task.", ExitCode.INVALID_INPUT)
    if len(child_ids) != len(set(child_ids)):
        _exit("The same child task ID cannot be repeated.", ExitCode.INVALID_INPUT)

    parent = _task_from_cache_or_api(client, parent_task_id, tasks_by_id)
    _ensure_task_in_project(parent, project_id)
    children: list[Task] = []
    for child_id in child_ids:
        child = _task_from_cache_or_api(client, child_id, tasks_by_id)
        _ensure_task_in_project(child, project_id)
        children.append(child)
    return parent, tuple(children), parent_task_id, child_ids


def _resolve_task_references(
    client: ActaskApiClient,
    project_id: str,
    parent_reference: str,
    child_references: list[str],
) -> tuple[str, list[str], dict[str, Task]]:
    """Resolve IDs directly and fall back to exact public keys in the project."""

    references = [parent_reference, *child_references]
    resolved: dict[str, str] = {}
    tasks_by_id: dict[str, Task] = {}
    unresolved: list[str] = []
    for reference in references:
        try:
            task = client.show_task(reference).task
        except NotFoundError:
            unresolved.append(reference)
            continue
        _ensure_task_in_project(task, project_id)
        resolved[reference] = task.id
        tasks_by_id[task.id] = task

    if unresolved:
        candidates_by_reference = _resolve_from_candidates(
            client,
            project_id,
            unresolved,
        )
        resolved.update(candidates_by_reference)

    return (
        resolved.get(parent_reference, parent_reference),
        [resolved.get(reference, reference) for reference in child_references],
        tasks_by_id,
    )


def _task_from_cache_or_api(
    client: ActaskApiClient,
    task_id: str,
    tasks_by_id: Mapping[str, Task],
) -> Task:
    task = tasks_by_id.get(task_id)
    return task if task is not None else client.show_task(task_id).task


def _resolve_from_candidates(
    client: ActaskApiClient,
    project_id: str,
    references: list[str],
) -> dict[str, str]:
    remaining = set(references)
    matches: dict[str, str] = {}
    page = 1
    while remaining:
        result = client.list_task_grouping_candidates(
            project_id,
            page=page,
            page_size=100,
        )
        for candidate in result.candidates:
            if candidate.id in remaining:
                matches[candidate.id] = candidate.id
                remaining.remove(candidate.id)
            if candidate.key in remaining:
                matches[candidate.key] = candidate.id
                remaining.remove(candidate.key)
        if not result.has_next or result.next_page is None or result.next_page == page:
            break
        page = result.next_page

    if remaining:
        reference = sorted(remaining)[0]
        _exit(
            f"Task reference {reference} was not found in project {project_id}.",
            ExitCode.NOT_FOUND,
        )
    return matches


def _ensure_task_in_project(task: Task, project_id: str) -> None:
    if task.project_id != project_id:
        _exit(
            f"Task {task.id} does not belong to project {project_id}.",
            ExitCode.INVALID_INPUT,
        )


def _find_operation(
    client: ActaskApiClient,
    project_id: str,
    operation_id: str,
) -> TaskGroupingOperation:
    page = 1
    while True:
        result = client.list_task_groupings(project_id, page=page, page_size=100)
        for operation in result.operations:
            if operation.id == operation_id:
                return operation
        if not result.has_next or result.next_page is None or result.next_page == page:
            break
        page = result.next_page
    _exit(
        f"Grouping operation {operation_id} was not found in project {project_id}.",
        ExitCode.NOT_FOUND,
    )


def _normalize_status(status: str | None) -> str | None:
    if status is None:
        return None
    normalized = status.strip().casefold()
    if normalized not in {"active", "undone"}:
        _exit("--status must be active or undone.", ExitCode.INVALID_INPUT)
    return normalized


def _page_meta(
    result: (
        TaskGroupingCandidatePageResult
        | TaskGroupingOperationPageResult
        | GroupedTaskPageResult
    ),
    request_id: str | None,
) -> dict[str, object]:
    return {
        "page": result.page,
        "page_size": result.page_size,
        "has_next": result.has_next,
        "next_page": result.next_page,
        "request_id": request_id,
    }


def _write_candidate_list(result: TaskGroupingCandidatePageResult) -> None:
    for candidate in result.candidates:
        role = _candidate_role(candidate)
        typer.echo(f"{candidate.key}\t{candidate.title}\t{candidate.id}\t{role}")
    _write_page_footer(result.page, result.page_size, len(result.candidates), result.has_next)


def _candidate_role(candidate: TaskGroupingCandidate) -> str:
    can_be_parent = candidate.payload.get("can_be_parent") is True
    can_be_child = candidate.payload.get("can_be_child") is True
    if can_be_parent and can_be_child:
        return "parent or child"
    if can_be_parent:
        return "parent"
    if can_be_child:
        return "child"
    if candidate.payload.get("is_grouped_task") is True:
        return "already grouped"
    return "not eligible"


def _write_grouped_task_list(result: GroupedTaskPageResult) -> None:
    for task in result.tasks:
        typer.echo(f"{task.key}\t{task.title}\t{task.id}")
    _write_page_footer(result.page, result.page_size, len(result.tasks), result.has_next)


def _write_operation_list(result: TaskGroupingOperationPageResult) -> None:
    for operation in result.operations:
        parent = _payload_string(operation.payload, "parent_task_key_snapshot") or operation.id
        item_count = _payload_integer(operation.payload, "item_count")
        typer.echo(f"{operation.id}\t{operation.status}\t{parent}\t{item_count}")
    _write_page_footer(
        result.page,
        result.page_size,
        len(result.operations),
        result.has_next,
    )


def _write_page_footer(page: int, page_size: int, count: int, has_next: bool) -> None:
    suffix = " (more available)" if has_next else ""
    typer.echo(f"Page {page} ({count} items; page size {page_size}){suffix}.")


def _write_operation_result(
    operation: TaskGroupingOperation,
    request_id: str | None,
    json_output: bool,
) -> None:
    if json_output:
        _write_json(operation.to_data(), {"request_id": request_id})
        return
    parent = _payload_string(operation.payload, "parent_task_key_snapshot") or operation.id
    item_count = _payload_integer(operation.payload, "item_count")
    typer.echo(
        f"{operation.id}\t{operation.status}\t{parent}\t{item_count} grouped task(s)"
    )


def _write_dry_run(payload: dict[str, object], json_output: bool) -> None:
    if json_output:
        _write_json(payload, {"dry_run": True})
        return
    typer.echo(f"Dry run: {payload}")


def _write_cancelled(json_output: bool) -> None:
    if json_output:
        _write_json(None, {"cancelled": True})
        return
    typer.echo("Cancelled.")


def _payload_string(payload: Mapping[str, object], field: str) -> str | None:
    value = payload.get(field)
    return value if isinstance(value, str) else None


def _payload_integer(payload: Mapping[str, object], field: str) -> int:
    value = payload.get(field)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    items = payload.get("items")
    return len(items) if isinstance(items, list) else 0


def _confirm(message: str, yes: bool) -> bool:
    return yes or typer.confirm(message)


def _require_non_empty(value: str, message: str) -> str:
    if not value.strip():
        _exit(message, ExitCode.INVALID_INPUT)
    return value.strip()


def _exit_api_error(error: ApiError) -> NoReturn:
    _exit(str(error), error.exit_code)


def _exit(message: str, exit_code: ExitCode) -> NoReturn:
    typer.echo(message, err=True)
    raise typer.Exit(int(exit_code))
