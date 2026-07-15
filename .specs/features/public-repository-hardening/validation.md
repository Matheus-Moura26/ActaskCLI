# Public Repository Hardening Validation

**Date**: 2026-07-15  
**Spec**: `.specs/features/public-repository-hardening/spec.md`  
**Diff range**: `9f70866..d1bdaa9` (feature commits `ba18d49..d1bdaa9`)  
**Verifier**: independent sub-agent (author != verifier)

## Verdict

**Overall: PASS**. The implementation satisfies the documented hardening controls, the full local gate passes, and all three scratch mutations are killed. Publication is intentionally the post-PASS step and is not an implementation gap.

## Task Completion

| Task | Status | Evidence |
| --- | --- | --- |
| T01-T04 | Done | Both feature commits and scoped diff inspected. |
| T05 | Done by this report | Independent full gate, outcome review, and scratch sensor executed. |
| T06 | Ready after PASS | GitHub repository is public; secret scanning, push protection, and Dependabot security updates are enabled. Branch publication follows this verifier PASS. |

## Requirement Evidence

| Requirement | Spec-defined outcome and evidence | Result |
| --- | --- | --- |
| PUB-001 | Official repository and release-only binary source: `README.md:33-43`, `SECURITY.md:3-9`; assertions at `tests/unit/test_release_docs.py:23-25`. | PASS |
| PUB-002 | Checksum verification before execution: `README.md:73-91`, `SECURITY.md:9`, `skills/actask-cli/SKILL.md:12`; assertions at `tests/unit/test_release_docs.py:12` and `tests/skill/test_skill_forward_workflows.py:82`. | PASS |
| PUB-003 | Credential prohibition and fictitious test data: `SECURITY.md:11-15`, `skills/actask-cli/SKILL.md:58`; diff/history pattern scan found no credential-shaped value and fixtures use reserved `example.test`. | PASS |
| PUB-004 | Every current workflow `uses:` entry has a 40-hex SHA and readable version comment (`.github/workflows/ci.yml:14-15`, `.github/workflows/release.yml:20-21,61-62,82,95-96`). `tests/unit/test_release_workflow.py:34-39` now rejects any external `uses:` reference without a full SHA. | PASS |
| PUB-005 | Workflow defaults are `contents: read`; only release job has `contents: write` (`ci.yml:7-8`, `release.yml:8-9,88-91`); assertion at `tests/unit/test_release_workflow.py:35-44`. | PASS |
| PUB-006 | `.github/dependabot.yml:1-12` covers `pip` and `github-actions`. GitHub API reports public visibility plus enabled secret scanning, push protection, and Dependabot security updates. | PASS |
| PUB-007 | Skill trusts only the official origin, requires checksum verification, and refuses credentials (`skills/actask-cli/SKILL.md:12,58`); assertions at `tests/skill/test_skill_forward_workflows.py:80-83`. | PASS |
| PUB-008 | Backend controls are explicitly deferred in `SECURITY.md:17-19` and `spec.md:25-31`. | PASS |

## Acceptance Criteria

| Criterion | Assertion evidence | Result |
| --- | --- | --- |
| Tests fail for mutable Actions and global `contents: write` | Generic immutable-reference assertion: `tests/unit/test_release_workflow.py:34-39`. Permission assertion: `tests/unit/test_release_workflow.py:42-51`. Both mutations were killed. | PASS |
| Tests fail if README/Skill omit official origin or checksum verification | `tests/unit/test_release_docs.py:12,23-25`; `tests/skill/test_skill_forward_workflows.py:81-83`. Skill checksum mutant was killed. | PASS |
| Full suite, lint, types, and build pass without ActaskBack alteration | Ruff PASS; mypy PASS (14 source files); pytest **57 passed**; build produced sdist and wheel. | PASS |
| Feature diff is wholly inside ActaskCLI | `git diff --name-status 9f70866..96c31a5` lists only ActaskCLI files. Separate ActaskBack worktree is clean; no backend command or edit was used. | PASS |

## Gate Check

- Commands: `.venv/Scripts/python.exe -m ruff check .`; `-m mypy`; `-m pytest -q`; `-m build`
- Result: Ruff PASS; mypy PASS; **57 passed, 0 failed, 0 skipped**; build PASS.
- Baseline at `9f70866`: **55 collected**. Delta: **+2 tests**.
- `git diff --check` reports only two trailing blank lines in new spec/design documents; non-blocking documentation hygiene.

## Discrimination Sensor

All mutations were made and discarded in temporary worktree `96c31a5`; the real implementation was never mutated.

| Mutation | Targeted test | Result |
| --- | --- | --- |
| Add previously unknown `uses: actions/cache@v4` to CI | `tests/unit/test_release_workflow.py` | KILLED: generic immutable-reference assertion reported the mutable entry. |
| Change release global permission from `contents: read` to `contents: write` | `tests/unit/test_release_workflow.py` | KILLED: expected least-privilege assertion failed. |
| Remove checksum-verification instruction from the Skill | `tests/skill/test_skill_forward_workflows.py` | KILLED: `SHA256SUMS` assertion failed. |

**Sensor result: 3/3 killed — PASS.**

## Code Quality

The diff is scoped and follows existing repository patterns. No production CLI behavior or ActaskBack code changed. The generic workflow assertion now quantifies over all external `uses:` entries and directly enforces the spec invariant.

## Ranked Gaps / Next Step

No implementation or verification gaps remain. Publish the feature branch while preserving the already-enabled GitHub security settings.

No requirement status was edited because the verifier is restricted to this report.
