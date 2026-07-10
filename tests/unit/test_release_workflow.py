from pathlib import Path


def test_release_workflow_builds_each_supported_platform_and_publishes_checksums() -> None:
    workflow = Path(".github/workflows/release.yml").read_text(encoding="utf-8")

    assert 'tags:\n      - "v[0-9]+.[0-9]+.[0-9]+"' in workflow
    assert "windows-x64" in workflow
    assert "linux-x64" in workflow
    assert "macos-x64" in workflow
    assert "macos-arm64" in workflow
    assert "python -m PyInstaller" in workflow
    assert "smoke_release_binary.py" in workflow
    assert "sha256sum actask-* > SHA256SUMS" in workflow
    assert "gh release create" in workflow
    assert "Verify release tag matches package version" in workflow
