import re
from pathlib import Path

PINNED_ACTIONS = (
    "actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4",
    "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5",
    "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02 # v4",
    "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093 # v4",
)


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


def test_workflows_pin_actions_and_apply_least_privilege() -> None:
    ci = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    release = Path(".github/workflows/release.yml").read_text(encoding="utf-8")
    workflows = ci + release

    for action in PINNED_ACTIONS:
        assert action in workflows
    mutable_actions = [
        line.strip()
        for line in workflows.splitlines()
        if re.search(r"\buses:\s+[^./\s][^\s]*@(?![0-9a-f]{40}\b)", line)
    ]
    assert mutable_actions == []
    assert "actions/checkout@v4" not in workflows
    assert "actions/setup-python@v5" not in workflows
    assert "permissions:\n  contents: read" in ci
    assert "permissions:\n  contents: read" in release
    assert "release:\n    name: Publish public GitHub release" in release
    release_permissions = (
        "release:\n"
        "    name: Publish public GitHub release\n"
        "    permissions:\n"
        "      contents: write"
    )
    assert release_permissions in release
