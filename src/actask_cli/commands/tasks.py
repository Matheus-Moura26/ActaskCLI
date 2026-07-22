"""Task commands that rely on backend authorization for every request."""

from __future__ import annotations

from typing import NoReturn

import typer

from actask_cli.client.errors import ApiError, ExitCode, UnauthenticatedError
from actask_cli.client.models import Task
from actask_cli.commands.auth import _active_session, _client, _delete_after_unauthenticated
from actask_cli.commands.projects import _write_json
from actask_cli.config.credentials import CredentialStore

app = typer.Typer(help="Read and modify tasks available to the active Actask user.")


@app.command("list")
def list_tasks(
    project_id: str = typer.Option(..., "--project", help="Project ID to query."),
    page: int = typer.Option(1, min=1, help="Page number."),
    page_size: int = typer.Option(25, min=1, help="Number of tasks per page."),
    query: str | None = typer.Option(None, help="Full-text task query."),
    filters: list[str] = typer.Option([], "--filter", help="Filter as field:operator:value."),
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON envelope."),
) -> None:
    """List tasks using the backend's authorized structured query route."""

    payload: dict[str, object] = {
        "project_id": _require_non_empty(project_id, "A project ID is required."),
        "page": page,
        "page_size": page_size,
    }
    if query is not None:
        payload["query"] = query
    if filters:
        payload["filters"] = [_parse_filter(item) for item in filters]

    profile, session_token = _active_session()
    credentials = CredentialStore()
    try:
        with _client(profile.server_url, session_token) as client:
            result = client.list_tasks(payload)
    except UnauthenticatedError as error:
        _delete_after_unauthenticated(credentials, profile)
        _exit_api_error(error)
    except ApiError as error:
        _exit_api_error(error)

    meta: dict[str, object] = {
        "page": result.page,
        "page_size": result.page_size,
        "total": result.total,
        "query_text": result.query_text,
        "applied_order": list(result.applied_order),
        "request_id": result.request_id,
    }
    if json_output:
        _write_json([task.to_data() for task in result.tasks], meta)
        return
    _write_task_list(result.tasks, meta)


@app.command("show")
def show_task(
    task_id: str,
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON envelope."),
) -> None:
    """Show one backend-authorized task."""

    _require_non_empty(task_id, "A task ID is required.")
    profile, session_token = _active_session()
    credentials = CredentialStore()
    try:
        with _client(profile.server_url, session_token) as client:
            result = client.show_task(task_id)
    except UnauthenticatedError as error:
        _delete_after_unauthenticated(credentials, profile)
        _exit_api_error(error)
    except ApiError as error:
        _exit_api_error(error)

    if json_output:
        _write_json(result.task.to_data(), {"request_id": result.request_id})
        return
    typer.echo(f"{result.task.key}\t{result.task.title}\t{result.task.project_id}\t{result.task.id}")


@app.command("create")
def create_task(
    project_id: str = typer.Option(..., "--project", help="Project ID for the new task."),
    title: str = typer.Option(..., help="Task title."),
    sprint: int = typer.Option(..., min=0, help="Sprint number."),
    description: str = typer.Option("", help="Task description."),
    column_id: str | None = typer.Option(None, help="Initial column ID."),
    assignee_id: str | None = typer.Option(None, help="Assignee user ID."),
    priority: str = typer.Option("normal", help="Task priority."),
    issue_type: str = typer.Option("task", "--issue-type", help="Task issue type."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show the normalized payload only."),
    yes: bool = typer.Option(False, "--yes", help="Confirm the change without a prompt."),
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON envelope."),
) -> None:
    """Create a task after explicit confirmation, unless dry-running."""

    payload = _create_payload(
        project_id,
        title,
        sprint,
        description,
        column_id,
        assignee_id,
        priority,
        issue_type,
    )
    if dry_run:
        _write_dry_run(payload, json_output)
        return
    if not _confirm("Create this task?", yes):
        _write_cancelled(json_output)
        return

    profile, session_token = _active_session()
    credentials = CredentialStore()
    try:
        with _client(profile.server_url, session_token) as client:
            result = client.create_task(payload)
    except UnauthenticatedError as error:
        _delete_after_unauthenticated(credentials, profile)
        _exit_api_error(error)
    except ApiError as error:
        _exit_api_error(error)
    _write_task_result(result.task, result.request_id, json_output)


@app.command("update")
def update_task(
    task_id: str,
    title: str | None = typer.Option(None, help="New task title."),
    description: str | None = typer.Option(None, help="New task description."),
    sprint: int | None = typer.Option(None, min=0, help="New sprint number."),
    column_id: str | None = typer.Option(None, help="New column ID."),
    assignee_id: str | None = typer.Option(None, help="New assignee user ID."),
    priority: str | None = typer.Option(None, help="New task priority."),
    issue_type: str | None = typer.Option(None, "--issue-type", help="New issue type."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show the normalized payload only."),
    yes: bool = typer.Option(False, "--yes", help="Confirm the change without a prompt."),
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON envelope."),
) -> None:
    """Update one task after explicit confirmation, unless dry-running."""

    normalized_task_id = _require_non_empty(task_id, "A task ID is required.")
    payload = _update_payload(
        title, description, sprint, column_id, assignee_id, priority, issue_type
    )
    move_column_id = payload.pop("column_id", None)
    if move_column_id is not None:
        assert isinstance(move_column_id, str)
    if move_column_id is not None and payload:
        _exit(
            "--column-id cannot be combined with other task fields; "
            "move the task in a separate command.",
            ExitCode.INVALID_INPUT,
        )
    if dry_run:
        _write_dry_run(
            {"move": {"column_id": move_column_id}} if move_column_id is not None else payload,
            json_output,
        )
        return
    if not _confirm("Update this task?", yes):
        _write_cancelled(json_output)
        return

    profile, session_token = _active_session()
    credentials = CredentialStore()
    try:
        with _client(profile.server_url, session_token) as client:
            if move_column_id is not None:
                result = client.move_task(normalized_task_id, move_column_id)
            else:
                result = client.update_task(normalized_task_id, payload)
    except UnauthenticatedError as error:
        _delete_after_unauthenticated(credentials, profile)
        _exit_api_error(error)
    except ApiError as error:
        _exit_api_error(error)
    _write_task_result(result.task, result.request_id, json_output)


def _parse_filter(value: str) -> dict[str, str]:
    parts = value.split(":", maxsplit=2)
    if len(parts) != 3 or not all(part.strip() for part in parts):
        _exit("Filters must use field:operator:value.", ExitCode.INVALID_INPUT)
    return {"field_key": parts[0], "operator": parts[1], "value": parts[2]}


def _create_payload(
    project_id: str,
    title: str,
    sprint: int,
    description: str,
    column_id: str | None,
    assignee_id: str | None,
    priority: str,
    issue_type: str,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "project_id": _require_non_empty(project_id, "A project ID is required."),
        "title": _require_non_empty(title, "A task title is required."),
        "sprint": sprint,
        "description": description,
        "priority": _require_non_empty(priority, "A task priority is required."),
        "type": _require_non_empty(issue_type, "An issue type is required."),
    }
    if column_id is not None:
        payload["column_id"] = _require_non_empty(column_id, "A column ID cannot be empty.")
    if assignee_id is not None:
        payload["assignee_id"] = _require_non_empty(assignee_id, "An assignee ID cannot be empty.")
    return payload


def _update_payload(
    title: str | None,
    description: str | None,
    sprint: int | None,
    column_id: str | None,
    assignee_id: str | None,
    priority: str | None,
    issue_type: str | None,
) -> dict[str, object]:
    optional_fields = {
        "title": title,
        "description": description,
        "sprint": sprint,
        "column_id": column_id,
        "assignee_id": assignee_id,
        "priority": priority,
        "type": issue_type,
    }
    payload: dict[str, object] = {
        key: value for key, value in optional_fields.items() if value is not None
    }
    if not payload:
        _exit("Provide at least one task field to update.", ExitCode.INVALID_INPUT)
    for field_name in ("title", "column_id", "assignee_id", "priority", "type"):
        value = payload.get(field_name)
        if isinstance(value, str) and not value.strip():
            _exit(f"{field_name} cannot be empty.", ExitCode.INVALID_INPUT)
    return payload


def _confirm(message: str, yes: bool) -> bool:
    return yes or typer.confirm(message)


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


def _write_task_result(task: Task, request_id: str | None, json_output: bool) -> None:
    if json_output:
        _write_json(task.to_data(), {"request_id": request_id})
        return
    typer.echo(f"{task.key}\t{task.title}\t{task.project_id}\t{task.id}")


def _require_non_empty(value: str, message: str) -> str:
    if not value.strip():
        _exit(message, ExitCode.INVALID_INPUT)
    return value


def _write_task_list(tasks: tuple[Task, ...], meta: dict[str, object]) -> None:
    for task in tasks:
        typer.echo(f"{task.key}\t{task.title}\t{task.project_id}\t{task.id}")
    typer.echo(f"Page {meta['page']} of {meta['total']} tasks.")


def _exit_api_error(error: ApiError) -> NoReturn:
    _exit(str(error), error.exit_code)


def _exit(message: str, exit_code: ExitCode) -> NoReturn:
    typer.echo(message, err=True)
    raise typer.Exit(int(exit_code))
