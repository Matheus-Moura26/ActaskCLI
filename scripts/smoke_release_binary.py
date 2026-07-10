"""Run the platform-neutral smoke check for a packaged Actask CLI binary."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Run ``actask version`` and verify that it identifies the CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    args = parser.parse_args()

    result = subprocess.run(
        [str(args.binary), "version"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return result.returncode
    if not result.stdout.startswith("actask "):
        sys.stderr.write("Smoke test did not receive Actask version output.\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
