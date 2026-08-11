"""Task commands that rely on backend authorization for every request."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import NoReturn, cast

import typer

from actask_cli.client.api import ActaskApiClient
from actask_cli.client.errors import ApiError, ExitCode, ServerError, UnauthenticatedError
from actask_cli.client.models import Case, Comment, Task
from actask_cli.commands.auth import _active_session, _client, _delete_after_unauthenticated
from actask_cli.commands.projects import _write_json
from actask_cli.config.credentials import CredentialStore

app = typer.Typer(help="Read and modify tasks available to the active Actask user.")
cases_app = typer.Typer(help="List and modify cases linked to a task.")
comments_app = typer.Typer(help="List and create comments linked to a task.")
app.add_typer(cases_app, name="cases")
app.add_typer(comments_app, name="comments")


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
    parent_id: str | None = typer.Option(
        None,
        "--parent-id",
        help="Parent task ID. Creates this task as a one-level subtask.",
    ),
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
        parent_id,
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
    position: int | None = typer.Option(
        None,
        min=0,
        help="Zero-based position in the target column; omitted means the end.",
    ),
    assignee_id: str | None = typer.Option(None, help="New assignee user ID."),
    priority: str | None = typer.Option(None, help="New task priority."),
    issue_type: str | None = typer.Option(None, "--issue-type", help="New issue type."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show the normalized payload only."),
    yes: bool = typer.Option(False, "--yes", help="Confirm the change without a prompt."),
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON envelope."),
) -> None:
    """Update one task after confirmation when unassigned or owned by this user."""

    normalized_task_id = _require_non_empty(task_id, "A task ID is required.")
    if position is not None and column_id is None:
        _exit("--position requires --column-id.", ExitCode.INVALID_INPUT)
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
            (
                {
                    "move": {
                        "column_id": move_column_id,
                        **({"position": position} if position is not None else {}),
                    }
                }
                if move_column_id is not None
                else payload
            ),
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
            _require_task_responsibility(client, normalized_task_id)
            if not _confirm("Update this task?", yes):
                _write_cancelled(json_output)
                return
            if move_column_id is not None:
                result = client.move_task(normalized_task_id, move_column_id, position)
            else:
                result = client.update_task(normalized_task_id, payload)
    except UnauthenticatedError as error:
        _delete_after_unauthenticated(credentials, profile)
        _exit_api_error(error)
    except ApiError as error:
        _exit_api_error(error)
    _write_task_result(result.task, result.request_id, json_output)


@comments_app.command("list")
def list_comments(
    task_id: str,
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON envelope."),
) -> None:
    """List the comments linked to one backend-authorized task."""

    normalized_task_id = _require_non_empty(task_id, "A task ID is required.")
    profile, session_token = _active_session()
    credentials = CredentialStore()
    try:
        with _client(profile.server_url, session_token) as client:
            result = client.list_comments(normalized_task_id)
    except UnauthenticatedError as error:
        _delete_after_unauthenticated(credentials, profile)
        _exit_api_error(error)
    except ApiError as error:
        _exit_api_error(error)

    if json_output:
        _write_json(
            [comment.to_data() for comment in result.comments],
            {
                "task_id": normalized_task_id,
                "total": len(result.comments),
                "request_id": result.request_id,
            },
        )
        return
    for comment in result.comments:
        typer.echo(f"{comment.id}\t{_comment_human_summary(comment)}")
    typer.echo(f"{len(result.comments)} comments.")


@comments_app.command("create")
def create_comment(
    task_id: str,
    content: str = typer.Option(
        ...,
        "--content",
        help="Comment text. Include @label in the text or pass explicit user IDs.",
    ),
    mention_user_ids: list[str] = typer.Option(
        [],
        "--mention-user-id",
        help="User ID to mention; repeat for multiple people.",
    ),
    parent_id: str | None = typer.Option(
        None,
        "--parent-id",
        help="Parent comment ID when replying to an existing comment.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show the normalized payload only."),
    yes: bool = typer.Option(False, "--yes", help="Confirm the change without a prompt."),
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON envelope."),
) -> None:
    """Create a comment and optional user mentions after confirmation."""

    normalized_task_id = _require_non_empty(task_id, "A task ID is required.")
    payload: dict[str, object] = {
        "content": _require_non_empty(content, "Comment content is required."),
        "mentioned_user_ids": _normalize_user_ids(
            mention_user_ids,
            "A mention user ID cannot be empty.",
        ),
    }
    if parent_id is not None:
        payload["parent_id"] = _require_non_empty(
            parent_id,
            "A parent comment ID cannot be empty.",
        )
    if dry_run:
        _write_dry_run(payload, json_output)
        return

    profile, session_token = _active_session()
    credentials = CredentialStore()
    try:
        with _client(profile.server_url, session_token) as client:
            _require_task_responsibility(client, normalized_task_id)
            if not _confirm("Create this comment?", yes):
                _write_cancelled(json_output)
                return
            result = client.create_comment(normalized_task_id, payload)
    except UnauthenticatedError as error:
        _delete_after_unauthenticated(credentials, profile)
        _exit_api_error(error)
    except ApiError as error:
        _exit_api_error(error)
    _write_comment_result(result.comment, result.request_id, json_output)


@cases_app.command("list")
def list_cases(
    task_id: str,
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON envelope."),
) -> None:
    """List the cases linked to one backend-authorized task."""

    normalized_task_id = _require_non_empty(task_id, "A task ID is required.")
    profile, session_token = _active_session()
    credentials = CredentialStore()
    try:
        with _client(profile.server_url, session_token) as client:
            result = client.show_task(normalized_task_id)
            cases = _cases_from_task(result.task, result.request_id)
    except UnauthenticatedError as error:
        _delete_after_unauthenticated(credentials, profile)
        _exit_api_error(error)
    except ApiError as error:
        _exit_api_error(error)

    if json_output:
        _write_json(
            [case.to_data() for case in cases],
            {
                "task_id": normalized_task_id,
                "total": len(cases),
                "request_id": result.request_id,
            },
        )
        return
    for case in cases:
        typer.echo(f"{case.id}\t{_case_human_summary(case)}")
    typer.echo(f"{len(cases)} cases.")


@cases_app.command("fields")
def list_case_fields(
    task_id: str,
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON envelope."),
) -> None:
    """List the case fields configured for the task's project."""

    normalized_task_id = _require_non_empty(task_id, "A task ID is required.")
    profile, session_token = _active_session()
    credentials = CredentialStore()
    try:
        with _client(profile.server_url, session_token) as client:
            task_result = client.show_task(normalized_task_id)
            fields_result = client.list_project_case_fields(task_result.task.project_id)
    except UnauthenticatedError as error:
        _delete_after_unauthenticated(credentials, profile)
        _exit_api_error(error)
    except ApiError as error:
        _exit_api_error(error)

    if json_output:
        _write_json(
            list(fields_result.entries),
            {
                "task_id": normalized_task_id,
                "project_id": task_result.task.project_id,
                "request_id": fields_result.request_id or task_result.request_id,
            },
        )
        return
    for field in fields_result.entries:
        field_id = field.get("id", "")
        label = field.get("label", "")
        field_type = field.get("field_type", "")
        typer.echo(f"{field_id}\t{label}\t{field_type}")


@cases_app.command("create")
def create_case(
    task_id: str,
    description: str = typer.Option("", help="Case description."),
    tenant_id: str | None = typer.Option(None, "--tenant-id", help="Customer or tenant ID."),
    person_ids: list[str] = typer.Option(
        [],
        "--person-id",
        help="Person ID linked to the case; repeat for multiple people.",
    ),
    motivo: str | None = typer.Option(None, help="Reason for the case."),
    solucao: str | None = typer.Option(None, help="Solution for the case."),
    field_values: str | None = typer.Option(
        None,
        "--field-values",
        help="Case custom fields as a JSON object keyed by field definition ID.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show the normalized payload only."),
    yes: bool = typer.Option(False, "--yes", help="Confirm the change without a prompt."),
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON envelope."),
) -> None:
    """Create a case linked to a task after validation and confirmation."""

    normalized_task_id = _require_non_empty(task_id, "A task ID is required.")
    normalized_field_values = _parse_json_object(field_values, "--field-values")
    payload = _case_create_payload(
        description,
        tenant_id,
        person_ids,
        motivo,
        solucao,
        normalized_field_values,
    )
    if dry_run:
        _write_dry_run(payload, json_output)
        return

    profile, session_token = _active_session()
    credentials = CredentialStore()
    try:
        with _client(profile.server_url, session_token) as client:
            task = _require_task_responsibility(client, normalized_task_id)
            _validate_case_field_values(
                client,
                task.project_id,
                normalized_field_values,
                require_required=True,
            )
            if not _confirm("Create this case?", yes):
                _write_cancelled(json_output)
                return
            result = client.create_case(normalized_task_id, payload)
    except UnauthenticatedError as error:
        _delete_after_unauthenticated(credentials, profile)
        _exit_api_error(error)
    except ApiError as error:
        _exit_api_error(error)
    _write_case_result(result.case, result.request_id, json_output)


@cases_app.command("update")
def update_case(
    task_id: str,
    case_id: str,
    description: str | None = typer.Option(None, help="New case description."),
    tenant_id: str | None = typer.Option(None, "--tenant-id", help="New customer or tenant ID."),
    person_ids: list[str] = typer.Option(
        [],
        "--person-id",
        help="New person ID linked to the case; repeat for multiple people.",
    ),
    clear_person_ids: bool = typer.Option(
        False,
        "--clear-person-ids",
        help="Remove all person IDs from the case.",
    ),
    is_done: str | None = typer.Option(
        None,
        "--is-done",
        help="Set completion state using true or false.",
    ),
    motivo: str | None = typer.Option(None, help="New reason for the case."),
    solucao: str | None = typer.Option(None, help="New solution for the case."),
    field_values: str | None = typer.Option(
        None,
        "--field-values",
        help="Case custom fields as a JSON object keyed by field definition ID.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show the normalized payload only."),
    yes: bool = typer.Option(False, "--yes", help="Confirm the change without a prompt."),
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON envelope."),
) -> None:
    """Update one case after validation and confirmation."""

    normalized_task_id = _require_non_empty(task_id, "A task ID is required.")
    normalized_case_id = _require_non_empty(case_id, "A case ID is required.")
    if person_ids and clear_person_ids:
        _exit(
            "--person-id cannot be combined with --clear-person-ids.",
            ExitCode.INVALID_INPUT,
        )
    normalized_field_values = (
        None if field_values is None else _parse_json_object(field_values, "--field-values")
    )
    payload = _case_update_payload(
        description,
        tenant_id,
        person_ids,
        clear_person_ids,
        is_done,
        motivo,
        solucao,
        normalized_field_values,
    )
    if dry_run:
        _write_dry_run(payload, json_output)
        return

    profile, session_token = _active_session()
    credentials = CredentialStore()
    try:
        with _client(profile.server_url, session_token) as client:
            task = _require_task_responsibility(client, normalized_task_id)
            if normalized_field_values is not None:
                _validate_case_field_values(
                    client,
                    task.project_id,
                    normalized_field_values,
                    require_required=False,
                )
            if not _confirm("Update this case?", yes):
                _write_cancelled(json_output)
                return
            result = client.update_case(normalized_task_id, normalized_case_id, payload)
    except UnauthenticatedError as error:
        _delete_after_unauthenticated(credentials, profile)
        _exit_api_error(error)
    except ApiError as error:
        _exit_api_error(error)
    _write_case_result(result.case, result.request_id, json_output)


def _cases_from_task(task: Task, request_id: str | None) -> tuple[Case, ...]:
    raw_cases = task.payload.get("cases", [])
    if not isinstance(raw_cases, list):
        raise ServerError(request_id=request_id)
    cases: list[Case] = []
    for raw_case in raw_cases:
        if not isinstance(raw_case, Mapping):
            raise ServerError(request_id=request_id)
        cases.append(Case.from_payload(raw_case, request_id))
    return tuple(cases)


def _case_human_summary(case: Case) -> str:
    state = "done" if case.payload.get("is_done") is True else "open"
    summary = case.payload.get("motivo") or case.payload.get("description") or ""
    normalized_summary = " ".join(str(summary).split())
    return f"{state}\t{normalized_summary}"


def _case_create_payload(
    description: str,
    tenant_id: str | None,
    person_ids: list[str],
    motivo: str | None,
    solucao: str | None,
    field_values: dict[str, object],
) -> dict[str, object]:
    payload: dict[str, object] = {
        "description": description,
        "person_ids": _normalize_person_ids(person_ids),
        "field_values": field_values,
    }
    if tenant_id is not None:
        payload["tenant_id"] = _require_non_empty(tenant_id, "A tenant ID cannot be empty.")
    if motivo is not None:
        payload["motivo"] = motivo
    if solucao is not None:
        payload["solucao"] = solucao
    return payload


def _case_update_payload(
    description: str | None,
    tenant_id: str | None,
    person_ids: list[str],
    clear_person_ids: bool,
    is_done: str | None,
    motivo: str | None,
    solucao: str | None,
    field_values: dict[str, object] | None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        key: value
        for key, value in {
            "description": description,
            "tenant_id": tenant_id,
            "motivo": motivo,
            "solucao": solucao,
        }.items()
        if value is not None
    }
    if person_ids:
        payload["person_ids"] = _normalize_person_ids(person_ids)
    elif clear_person_ids:
        payload["person_ids"] = []
    if is_done is not None:
        payload["is_done"] = _parse_boolean(is_done, "--is-done")
    if field_values is not None:
        payload["field_values"] = field_values
    if not payload:
        _exit("Provide at least one case field to update.", ExitCode.INVALID_INPUT)
    if tenant_id is not None and not tenant_id.strip():
        _exit("A tenant ID cannot be empty.", ExitCode.INVALID_INPUT)
    return payload


def _normalize_person_ids(person_ids: list[str]) -> list[str]:
    normalized: list[str] = []
    for person_id in person_ids:
        normalized.append(_require_non_empty(person_id, "A person ID cannot be empty."))
    return normalized


def _normalize_user_ids(user_ids: list[str], message: str) -> list[str]:
    normalized: list[str] = []
    for user_id in user_ids:
        normalized.append(_require_non_empty(user_id, message))
    return normalized


def _parse_boolean(value: str, option_name: str) -> bool:
    normalized = value.strip().casefold()
    if normalized in {"true", "1", "yes", "sim"}:
        return True
    if normalized in {"false", "0", "no", "não", "nao"}:
        return False
    _exit(f"{option_name} must be true or false.", ExitCode.INVALID_INPUT)


def _parse_json_object(value: str | None, option_name: str) -> dict[str, object]:
    if value is None:
        return {}
    try:
        parsed: object = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        _exit(f"{option_name} must be a valid JSON object.", ExitCode.INVALID_INPUT)
    if not isinstance(parsed, dict) or not all(isinstance(key, str) for key in parsed):
        _exit(f"{option_name} must be a valid JSON object.", ExitCode.INVALID_INPUT)
    return cast(dict[str, object], parsed)


def _validate_case_field_values(
    client: ActaskApiClient,
    project_id: str,
    field_values: Mapping[str, object],
    *,
    require_required: bool,
) -> None:
    fields_result = client.list_project_case_fields(project_id)
    definitions: dict[str, Mapping[str, object]] = {}
    for field_definition in fields_result.entries:
        field_id = field_definition.get("id")
        field_type = field_definition.get("field_type")
        if not isinstance(field_id, str) or not isinstance(field_type, str):
            raise ServerError(request_id=fields_result.request_id)
        definitions[field_id] = field_definition

    for field_id, value in field_values.items():
        selected_definition = definitions.get(field_id)
        if selected_definition is None:
            _exit(
                f"Case field '{field_id}' does not belong to this project.",
                ExitCode.INVALID_INPUT,
            )
        if selected_definition.get("is_active") is False:
            _exit(f"Case field '{field_id}' is inactive.", ExitCode.INVALID_INPUT)
        _validate_case_field_value(
            field_id,
            selected_definition,
            value,
            fields_result.request_id,
        )

    if require_required:
        for field_id, definition in definitions.items():
            missing_required = _case_value_is_empty(field_values.get(field_id))
            if _case_field_is_required(definition) and missing_required:
                _exit(
                    f"Required case field '{field_id}' must be provided.",
                    ExitCode.INVALID_INPUT,
                )


def _validate_case_field_value(
    field_id: str,
    definition: Mapping[str, object],
    value: object,
    request_id: str | None,
) -> None:
    if _case_value_is_empty(value):
        return
    field_type = definition.get("field_type")
    if not isinstance(field_type, str):
        raise ServerError(request_id=request_id)
    option_values = _case_field_option_values(definition, request_id)
    if field_type == "text":
        if not isinstance(value, str):
            _exit(f"Case field '{field_id}' expects text.", ExitCode.INVALID_INPUT)
        return
    if field_type == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            _exit(f"Case field '{field_id}' expects a number.", ExitCode.INVALID_INPUT)
        if isinstance(value, float) and not math.isfinite(value):
            _exit(f"Case field '{field_id}' expects a finite number.", ExitCode.INVALID_INPUT)
        return
    if field_type == "select_single":
        if not isinstance(value, str) or value not in option_values:
            _exit(
                f"Case field '{field_id}' expects one of the configured options.",
                ExitCode.INVALID_INPUT,
            )
        return
    if field_type == "select_multi":
        if (
            not isinstance(value, list)
            or not all(isinstance(item, str) for item in value)
            or any(item not in option_values for item in value)
        ):
            _exit(
                f"Case field '{field_id}' expects a list of configured options.",
                ExitCode.INVALID_INPUT,
            )
        return
    raise ServerError(request_id=request_id)


def _case_field_option_values(
    definition: Mapping[str, object],
    request_id: str | None,
) -> set[str]:
    raw_options = definition.get("options", [])
    if raw_options is None:
        return set()
    if not isinstance(raw_options, list):
        raise ServerError(request_id=request_id)
    values: set[str] = set()
    for option in raw_options:
        if not isinstance(option, Mapping) or not isinstance(option.get("value"), str):
            raise ServerError(request_id=request_id)
        values.add(cast(str, option["value"]))
    return values


def _case_field_is_required(definition: Mapping[str, object]) -> bool:
    if definition.get("is_required") is True:
        return True
    settings = definition.get("settings_json")
    return isinstance(settings, Mapping) and settings.get("required") is True


def _case_value_is_empty(value: object) -> bool:
    return value is None or value == "" or value == []


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
    parent_id: str | None,
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
    if parent_id is not None:
        payload["parent_id"] = _require_non_empty(parent_id, "A parent task ID cannot be empty.")
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


def _require_task_responsibility(client: ActaskApiClient, task_id: str) -> Task:
    """Block CLI writes unless the task is unassigned or owned by this user.

    This is a CLI-side guardrail for the requested command behavior. The API
    remains the authorization authority for every write request.
    """

    identity = client.whoami()
    task = client.show_task(task_id).task
    if "assignee_id" not in task.payload:
        _exit(
            "A CLI não conseguiu confirmar o responsável desta task.",
            ExitCode.NETWORK_OR_SERVER,
        )
    assignee_id = task.payload["assignee_id"]
    if assignee_id is None or assignee_id == identity.user.id:
        return task
    _exit("Você não é o responsável desta task", ExitCode.FORBIDDEN)


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


def _write_case_result(case: Case, request_id: str | None, json_output: bool) -> None:
    if json_output:
        _write_json(case.to_data(), {"request_id": request_id})
        return
    typer.echo(f"{case.id}\t{_case_human_summary(case)}")


def _write_comment_result(comment: Comment, request_id: str | None, json_output: bool) -> None:
    if json_output:
        _write_json(comment.to_data(), {"request_id": request_id})
        return
    typer.echo(f"{comment.id}\t{_comment_human_summary(comment)}")


def _comment_human_summary(comment: Comment) -> str:
    author = comment.payload.get("author_name") or comment.payload.get("user_id") or ""
    content = " ".join(str(comment.payload.get("content", "")).split())
    return f"{author}\t{content}"


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
