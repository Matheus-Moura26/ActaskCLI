"""Interactive authentication commands."""

from typing import NoReturn

import typer

from actask_cli.client.api import ActaskApiClient
from actask_cli.client.errors import ApiError, ExitCode, UnauthenticatedError
from actask_cli.config.credentials import CredentialStore, CredentialStoreError
from actask_cli.config.profiles import ProfileError, ProfileStore, ServerProfile

app = typer.Typer(help="Authenticate this CLI with Actask.")


def _profile_store() -> ProfileStore:
    return ProfileStore.default()


def _credential_store() -> CredentialStore:
    return CredentialStore()


def _client(base_url: str, session_token: str | None = None) -> ActaskApiClient:
    return ActaskApiClient(base_url, session_token)


@app.command()
def login() -> None:
    """Create a session for an Actask server profile."""

    server_url = typer.prompt("Server URL")
    email = typer.prompt("Email")
    password = typer.prompt("Password", hide_input=True)
    try:
        profile = ServerProfile.create(server_url, email)
    except ProfileError as error:
        _exit(str(error), ExitCode.INVALID_INPUT)

    try:
        with _client(profile.server_url) as client:
            result = client.login(profile.email, password)
        _credential_store().set(profile, result.session_token)
        _profile_store().save_active(profile)
    except CredentialStoreError as error:
        _exit(str(error), ExitCode.NETWORK_OR_SERVER)
    except ApiError as error:
        _exit_api_error(error)

    typer.echo(f"Logged in as {result.user.email}.")


@app.command()
def logout() -> None:
    """Invalidate the active Actask session and remove it locally."""

    profile, session_token = _active_session()
    credentials = _credential_store()
    try:
        with _client(profile.server_url, session_token) as client:
            client.logout()
    except UnauthenticatedError as error:
        _delete_after_unauthenticated(credentials, profile)
        _exit_api_error(error)
    except ApiError as error:
        _exit_api_error(error)

    try:
        credentials.delete(profile)
    except CredentialStoreError as error:
        _exit(str(error), ExitCode.NETWORK_OR_SERVER)
    typer.echo("Logged out.")


@app.command()
def whoami() -> None:
    """Validate the active session and show the current identity."""

    profile, session_token = _active_session()
    credentials = _credential_store()
    try:
        with _client(profile.server_url, session_token) as client:
            identity = client.whoami()
    except UnauthenticatedError as error:
        _delete_after_unauthenticated(credentials, profile)
        _exit_api_error(error)
    except ApiError as error:
        _exit_api_error(error)

    typer.echo(f"{identity.user.name} <{identity.user.email}>")


def _active_session() -> tuple[ServerProfile, str]:
    try:
        profile = _profile_store().active()
        if profile is None:
            _exit_not_authenticated()
        session_token = _credential_store().get(profile)
    except ProfileError as error:
        _exit(str(error), ExitCode.INVALID_INPUT)
    except CredentialStoreError as error:
        _exit(str(error), ExitCode.NETWORK_OR_SERVER)
    if session_token is None:
        _exit_not_authenticated()
    return profile, session_token


def _delete_after_unauthenticated(credentials: CredentialStore, profile: ServerProfile) -> None:
    try:
        credentials.delete(profile)
    except CredentialStoreError:
        return


def _exit_not_authenticated() -> NoReturn:
    _exit("No active session. Run 'actask login'.", ExitCode.NOT_AUTHENTICATED)


def _exit_api_error(error: ApiError) -> NoReturn:
    _exit(str(error), error.exit_code)


def _exit(message: str, exit_code: ExitCode) -> NoReturn:
    typer.echo(message, err=True)
    raise typer.Exit(int(exit_code))
