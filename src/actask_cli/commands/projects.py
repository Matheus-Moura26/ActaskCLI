"""Project commands."""

from __future__ import annotations

import json
from typing import NoReturn

import typer

from actask_cli.client.errors import ApiError, ExitCode, UnauthenticatedError
from actask_cli.client.models import Project
from actask_cli.commands.auth import _active_session, _client, _delete_after_unauthenticated
from actask_cli.config.credentials import CredentialStore

app = typer.Typer(help="Read and create projects available to the active Actask user.")


@app.command("list")
def list_projects(
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON envelope."),
    page: int = typer.Option(1, min=1, help="Page number for local display pagination."),
    page_size: int = typer.Option(25, min=1, help="Number of projects per page."),
) -> None:
    """List projects authorized by the Actask backend."""

    profile, session_token = _active_session()
    credentials = CredentialStore()
    try:
        with _client(profile.server_url, session_token) as client:
            result = client.list_projects()
    except UnauthenticatedError as error:
        _delete_after_unauthenticated(credentials, profile)
        _exit_api_error(error)
    except ApiError as error:
        _exit_api_error(error)

    projects, meta = _page_projects(result.projects, page, page_size)
    meta["request_id"] = result.request_id
    if json_output:
        _write_json([project.to_data() for project in projects], meta)
        return
    _write_project_list(projects, meta)


@app.command("create")
def create_project(
    name: str = typer.Option(..., "--name", help="Project name."),
    key: str = typer.Option(..., "--key", help="Project key."),
    current_sprint: int = typer.Option(
        1,
        "--current-sprint",
        help="Initial sprint number.",
    ),
    timezone: str = typer.Option(
        "America/Sao_Paulo",
        "--timezone",
        help="IANA timezone for the project.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show the normalized payload only."),
    yes: bool = typer.Option(False, "--yes", help="Confirm the change without a prompt."),
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON envelope."),
) -> None:
    """Create a project after explicit confirmation, unless dry-running."""

    payload = _create_project_payload(name, key, current_sprint, timezone)
    if dry_run:
        _write_dry_run(payload, json_output)
        return
    if not _confirm("Create this project?", yes):
        _write_cancelled(json_output)
        return

    profile, session_token = _active_session()
    credentials = CredentialStore()
    try:
        with _client(profile.server_url, session_token) as client:
            result = client.create_project(payload)
    except UnauthenticatedError as error:
        _delete_after_unauthenticated(credentials, profile)
        _exit_api_error(error)
    except ApiError as error:
        _exit_api_error(error)
    _write_project_result(result.project, result.request_id, json_output)


@app.command("show")
def show_project(
    project_id: str,
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON envelope."),
) -> None:
    """Show one backend-authorized project."""

    if not project_id.strip():
        _exit("A project ID is required.", ExitCode.INVALID_INPUT)
    profile, session_token = _active_session()
    credentials = CredentialStore()
    try:
        with _client(profile.server_url, session_token) as client:
            result = client.show_project(project_id)
    except UnauthenticatedError as error:
        _delete_after_unauthenticated(credentials, profile)
        _exit_api_error(error)
    except ApiError as error:
        _exit_api_error(error)

    if json_output:
        _write_json(result.project.to_data(), {"request_id": result.request_id})
        return
    typer.echo(f"{result.project.key}\t{result.project.name}\t{result.project.id}")


@app.command("columns")
def list_project_columns(
    project_id: str,
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON envelope."),
) -> None:
    """List columns configured for one backend-authorized project."""

    _write_project_catalog(project_id, json_output, "list_project_columns")


@app.command("fields")
def list_project_fields(
    project_id: str,
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON envelope."),
) -> None:
    """List filterable field definitions and configured options for one project."""

    _write_project_catalog(project_id, json_output, "list_project_field_registry")


def _write_project_catalog(project_id: str, json_output: bool, method_name: str) -> None:
    if not project_id.strip():
        _exit("A project ID is required.", ExitCode.INVALID_INPUT)
    profile, session_token = _active_session()
    credentials = CredentialStore()
    try:
        with _client(profile.server_url, session_token) as client:
            result = getattr(client, method_name)(project_id)
    except UnauthenticatedError as error:
        _delete_after_unauthenticated(credentials, profile)
        _exit_api_error(error)
    except ApiError as error:
        _exit_api_error(error)

    entries = [dict(entry) for entry in result.entries]
    if json_output:
        _write_json(entries, {"request_id": result.request_id})
        return
    for entry in entries:
        identifier = entry.get("id", entry.get("key", ""))
        label = entry.get("name", entry.get("label", ""))
        typer.echo(f"{identifier}\t{label}")


def _page_projects(
    projects: tuple[Project, ...], page: int, page_size: int
) -> tuple[tuple[Project, ...], dict[str, object]]:
    start = (page - 1) * page_size
    return projects[start : start + page_size], {
        "page": page,
        "page_size": page_size,
        "total": len(projects),
    }


def _write_project_list(projects: tuple[Project, ...], meta: dict[str, object]) -> None:
    for project in projects:
        typer.echo(f"{project.key}\t{project.name}\t{project.id}")
    typer.echo(f"Page {meta['page']} of {meta['total']} projects.")


def _create_project_payload(
    name: str,
    key: str,
    current_sprint: int,
    timezone: str,
) -> dict[str, object]:
    return {
        "name": _require_non_empty(name, "A project name is required."),
        "key": _require_non_empty(key, "A project key is required.").upper(),
        "current_sprint": current_sprint,
        "timezone": _require_non_empty(timezone, "A project timezone is required."),
    }


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


def _write_project_result(
    project: Project,
    request_id: str | None,
    json_output: bool,
) -> None:
    if json_output:
        _write_json(project.to_data(), {"request_id": request_id})
        return
    typer.echo(f"{project.key}\t{project.name}\t{project.id}")


def _write_json(data: object, meta: dict[str, object]) -> None:
    typer.echo(json.dumps({"data": data, "meta": meta, "error": None}, sort_keys=True))


def _exit_api_error(error: ApiError) -> NoReturn:
    _exit(str(error), error.exit_code)


def _exit(message: str, exit_code: ExitCode) -> NoReturn:
    typer.echo(message, err=True)
    raise typer.Exit(int(exit_code))


def _require_non_empty(value: str, message: str) -> str:
    if not value.strip():
        _exit(message, ExitCode.INVALID_INPUT)
    return value
