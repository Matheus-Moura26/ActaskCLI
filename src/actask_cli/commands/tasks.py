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


def _parse_filter(value: str) -> dict[str, str]:
    parts = value.split(":", maxsplit=2)
    if len(parts) != 3 or not all(part.strip() for part in parts):
        _exit("Filters must use field:operator:value.", ExitCode.INVALID_INPUT)
    return {"field_key": parts[0], "operator": parts[1], "value": parts[2]}


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
