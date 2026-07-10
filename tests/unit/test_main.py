from typer.testing import CliRunner

from actask_cli.main import app

runner = CliRunner()


def test_help_is_available() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Operate Actask from the command line." in result.output
    assert "version" in result.output


def test_version_shows_cli_version() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert result.output == "actask 0.1.0\n"
