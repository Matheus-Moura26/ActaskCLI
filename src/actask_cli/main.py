"""Typer application entry point."""

import typer

from actask_cli import __version__
from actask_cli.commands.auth import app as auth_app
from actask_cli.commands.projects import app as projects_app
from actask_cli.config.profiles import ProfileError, ProfileStore

app = typer.Typer(
    help="Operate Actask from the command line.",
    no_args_is_help=True,
)
app.add_typer(auth_app)
app.add_typer(projects_app, name="projects")


def _profile_store() -> ProfileStore:
    return ProfileStore.default()


@app.callback()
def main() -> None:
    """Operate Actask from the command line."""


@app.command()
def version() -> None:
    """Show the installed CLI version and server profile."""
    try:
        profile = _profile_store().active()
    except ProfileError:
        profile = None
    server_url = profile.server_url if profile is not None else "not configured"
    typer.echo(f"actask {__version__}\nserver: {server_url}")
