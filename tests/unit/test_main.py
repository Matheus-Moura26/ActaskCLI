from typer.testing import CliRunner

import actask_cli.main as main
from actask_cli.config.profiles import ServerProfile

runner = CliRunner()


def test_help_is_available() -> None:
    result = runner.invoke(main.app, ["--help"])

    assert result.exit_code == 0
    assert "Operate Actask from the command line." in result.output
    assert "version" in result.output


def test_version_shows_cli_version_and_server_profile(monkeypatch) -> None:
    profile = ServerProfile.create("https://actask.example.test", "member@example.test")

    class FakeProfileStore:
        def active(self) -> ServerProfile:
            return profile

    monkeypatch.setattr(main, "_profile_store", FakeProfileStore)

    result = runner.invoke(main.app, ["version"])

    assert result.exit_code == 0
    assert result.output == "actask 0.1.0\nserver: https://actask.example.test\n"
