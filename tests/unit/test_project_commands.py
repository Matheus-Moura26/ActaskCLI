from __future__ import annotations

import json
from dataclasses import dataclass

from typer.testing import CliRunner

from actask_cli.client.errors import ForbiddenError, MethodNotAllowedError
from actask_cli.client.models import Project, ProjectCatalogResult, ProjectListResult, ProjectResult
from actask_cli.commands import projects
from actask_cli.config.profiles import ServerProfile
from actask_cli.main import app

PROFILE = ServerProfile.create("https://actask.example.test", "member@example.test")
PROJECT_ONE = Project(
    id="project-1",
    name="Example Project",
    key="EX",
    payload={"id": "project-1", "name": "Example Project", "key": "EX"},
)
PROJECT_TWO = Project(
    id="project-2",
    name="Second Project",
    key="SC",
    payload={"id": "project-2", "name": "Second Project", "key": "SC"},
)
runner = CliRunner()


class FakeCredentialStore:
    def __init__(self) -> None:
        self.deleted = False

    def delete(self, profile: ServerProfile) -> None:
        self.deleted = True


@dataclass
class FakeClient:
    projects: tuple[Project, ...] = (PROJECT_ONE, PROJECT_TWO)
    forbidden: bool = False

    def __enter__(self) -> FakeClient:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def list_projects(self) -> ProjectListResult:
        return ProjectListResult(self.projects, "req-projects")

    def show_project(self, project_id: str) -> ProjectResult:
        if self.forbidden:
            raise ForbiddenError("req-forbidden")
        return ProjectResult(PROJECT_ONE, "req-project")

    def list_project_columns(self, project_id: str) -> ProjectCatalogResult:
        if self.forbidden:
            raise ForbiddenError("req-forbidden")
        return ProjectCatalogResult(
            entries=({"id": "column-pending", "name": "Pendentes"},),
            request_id="req-columns",
        )

    def list_project_field_registry(self, project_id: str) -> ProjectCatalogResult:
        if self.forbidden:
            raise ForbiddenError("req-forbidden")
        return ProjectCatalogResult(
            entries=(
                {
                    "key": "status",
                    "label": "Status",
                    "options": [{"value": "column-pending", "label": "Pendentes"}],
                },
            ),
            request_id="req-fields",
        )


def _install_fakes(monkeypatch, client: FakeClient, credentials: FakeCredentialStore) -> None:
    monkeypatch.setattr(projects, "_active_session", lambda: (PROFILE, "<redacted-session-token>"))
    monkeypatch.setattr(projects, "_client", lambda base_url, session_token: client)
    monkeypatch.setattr(projects, "CredentialStore", lambda: credentials)


def test_projects_list_has_equivalent_human_and_json_output(monkeypatch) -> None:
    credentials = FakeCredentialStore()
    _install_fakes(monkeypatch, FakeClient(), credentials)

    human = runner.invoke(app, ["projects", "list"])
    json_result = runner.invoke(app, ["projects", "list", "--json"])

    payload = json.loads(json_result.output)
    assert human.exit_code == 0
    assert human.output == (
        "EX\tExample Project\tproject-1\n"
        "SC\tSecond Project\tproject-2\n"
        "Page 1 of 2 projects.\n"
    )
    assert json_result.exit_code == 0
    assert payload == {
        "data": [PROJECT_ONE.to_data(), PROJECT_TWO.to_data()],
        "error": None,
        "meta": {"page": 1, "page_size": 25, "request_id": "req-projects", "total": 2},
    }


def test_projects_list_pages_the_server_authorized_projects(monkeypatch) -> None:
    credentials = FakeCredentialStore()
    _install_fakes(monkeypatch, FakeClient(), credentials)

    result = runner.invoke(app, ["projects", "list", "--page", "2", "--page-size", "1", "--json"])

    payload = json.loads(result.output)
    assert result.exit_code == 0
    assert payload["data"] == [PROJECT_TWO.to_data()]
    assert payload["meta"] == {"page": 2, "page_size": 1, "request_id": "req-projects", "total": 2}


def test_projects_show_has_equivalent_human_and_json_output(monkeypatch) -> None:
    credentials = FakeCredentialStore()
    _install_fakes(monkeypatch, FakeClient(), credentials)

    human = runner.invoke(app, ["projects", "show", "project-1"])
    json_result = runner.invoke(app, ["projects", "show", "project-1", "--json"])
    payload = json.loads(json_result.output)

    assert human.exit_code == 0
    assert json_result.exit_code == 0
    assert human.output == (
        f"{payload['data']['key']}\t{payload['data']['name']}\t{payload['data']['id']}\n"
    )
    assert payload == {
        "data": PROJECT_ONE.to_data(),
        "error": None,
        "meta": {"request_id": "req-project"},
    }


def test_projects_show_preserves_forbidden_response(monkeypatch) -> None:
    credentials = FakeCredentialStore()
    _install_fakes(monkeypatch, FakeClient(forbidden=True), credentials)

    result = runner.invoke(app, ["projects", "show", "project-other"])

    assert result.exit_code == 4
    assert result.stderr == "You do not have permission to perform this action.\n"


def test_projects_show_reports_contract_incompatibility_without_retrying(monkeypatch) -> None:
    class ContractFailureClient(FakeClient):
        def show_project(self, project_id: str) -> ProjectResult:
            raise MethodNotAllowedError("req-method")

    credentials = FakeCredentialStore()
    _install_fakes(monkeypatch, ContractFailureClient(), credentials)

    result = runner.invoke(app, ["projects", "show", "project-1", "--json"])

    assert result.exit_code == 7
    assert result.stderr == (
        "Actask API contract error: this CLI command is not supported by the server endpoint.\n"
    )


def test_projects_columns_and_fields_expose_project_configuration(monkeypatch) -> None:
    credentials = FakeCredentialStore()
    _install_fakes(monkeypatch, FakeClient(), credentials)

    columns = runner.invoke(app, ["projects", "columns", "project-1", "--json"])
    fields = runner.invoke(app, ["projects", "fields", "project-1", "--json"])

    assert columns.exit_code == 0
    assert json.loads(columns.output) == {
        "data": [{"id": "column-pending", "name": "Pendentes"}],
        "error": None,
        "meta": {"request_id": "req-columns"},
    }
    assert fields.exit_code == 0
    assert json.loads(fields.output)["data"][0]["options"] == [
        {"label": "Pendentes", "value": "column-pending"}
    ]


def test_projects_catalog_preserves_forbidden_response(monkeypatch) -> None:
    credentials = FakeCredentialStore()
    _install_fakes(monkeypatch, FakeClient(forbidden=True), credentials)

    result = runner.invoke(app, ["projects", "columns", "project-other", "--json"])

    assert result.exit_code == 4
    assert result.stderr == "You do not have permission to perform this action.\n"
