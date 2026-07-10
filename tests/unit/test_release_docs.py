from pathlib import Path


def test_release_documentation_covers_supported_install_paths_and_checksum_verification() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    notes = Path("RELEASE_NOTES.md").read_text(encoding="utf-8")

    assert "actask-windows-x64.exe" in readme
    assert "actask-linux-x64" in readme
    assert "actask-macos-x64" in readme
    assert "actask-macos-arm64" in readme
    assert "SHA256SUMS" in readme
    assert "pipx install" in readme
    assert "git clone" in readme
    assert "# Actask CLI v1.0.0" in notes
    assert "SHA256SUMS" in notes
