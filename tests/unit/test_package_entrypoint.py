import subprocess
import sys


def test_module_entrypoint_runs_version_command() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "actask_cli", "version"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout.startswith("actask ")
