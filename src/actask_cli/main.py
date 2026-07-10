"""Typer application entry point."""

import typer

from actask_cli import __version__

app = typer.Typer(
    help="Operate Actask from the command line.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Operate Actask from the command line."""


@app.command()
def version() -> None:
    """Show the installed CLI version."""
    typer.echo(f"actask {__version__}")
