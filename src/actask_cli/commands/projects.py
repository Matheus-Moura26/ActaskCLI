"""Read-only project commands."""

from __future__ import annotations

import json
from typing import NoReturn

import typer

from actask_cli.client.errors import ApiError, ExitCode, UnauthenticatedError
from actask_cli.client.models import Project
from actask_cli.commands.auth import _active_session, _client, _delete_after_unauthenticated
from actask_cli.config.credentials import CredentialStore

app = typer.Typer(help="Read projects available to the active Actask user.")


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


def _write_json(data: object, meta: dict[str, object]) -> None:
    typer.echo(json.dumps({"data": data, "meta": meta, "error": None}, sort_keys=True))


def _exit_api_error(error: ApiError) -> NoReturn:
    _exit(str(error), error.exit_code)


def _exit(message: str, exit_code: ExitCode) -> NoReturn:
    typer.echo(message, err=True)
    raise typer.Exit(int(exit_code))
