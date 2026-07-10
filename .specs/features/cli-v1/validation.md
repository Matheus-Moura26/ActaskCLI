# CLI-V1 Validation

**Date**: 2026-07-10
**Spec**: `.specs/features/cli-v1/spec.md`
**Diff range**: `26e0202..HEAD`
**Verifier**: independent verifier, second pass (author != verifier)
**Focus commits**: `a319b55` (`test: close AC-05 and AC-06 coverage gaps`), `cab94f9` (`docs: record validation remediation evidence`)

---

## Verdict

**Overall**: PASS for all v1 acceptance criteria.  
**Release status**: `v1.0.0` published privately.  
**Remote evidence**: GitHub Actions run `29120601408` built and smoke-tested all supported binaries, then published `SHA256SUMS`.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T01-T14 | ✅ Done | All tasks are marked `[x]` in [`tasks.md`](/C:/Users/Acdev/RiderProjects/ActaskCLI/.specs/features/cli-v1/tasks.md). |

---

## Diff Review

- `a319b55` adds the missing verification for:
  - `whoami`, `projects show`, and `tasks show` human/JSON semantic equivalence
  - `tasks update --dry-run --json` normalized payload and no-network behavior
- `cab94f9` records the remediation in [`STATE.md`](/C:/Users/Acdev/RiderProjects/ActaskCLI/.specs/STATE.md) and [`tasks.md`](/C:/Users/Acdev/RiderProjects/ActaskCLI/.specs/features/cli-v1/tasks.md), including the direct backend execution evidence.
- `git diff --check 26e0202..HEAD` passed.
- Secret-pattern scan over `git log -p 26e0202..HEAD` found no credential-like material; repository occurrences are redacted placeholders only.

---

## Spec-Anchored Acceptance Criteria

| AC | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| AC-01 | Credentials do not appear in CLI args, stdout, stderr, logs, traces, or fixtures. | `tests/unit/test_auth_commands.py:113-115` asserts redacted password and session token are absent from CLI output; `tests/unit/test_credentials.py:41-61` asserts the session token is not written to profile config and is not echoed in keyring errors; fixture/spec scan shows only `<redacted-session-token>`. | ✅ PASS |
| AC-02 | Non-member gets `403` for another project's tasks via CLI and direct backend call. | CLI: `tests/unit/test_task_commands.py:129-146` asserts exit code `4` and the forbidden stderr for foreign project/task. Direct backend: `C:/Users/Acdev/RiderProjects/ActaskBack/tests/test_cli_v1_authorization.py:96-108` asserts `403` for outsider task query and `401` when session is missing; executed successfully with `6 passed`. | ✅ PASS |
| AC-03 | Authorized user can list and read project tasks. | CLI/client: `tests/unit/test_task_commands.py:80-126` asserts authorized list output, filters, and JSON envelope; `tests/unit/test_task_commands.py:149-167` asserts authorized task show output/envelope; `tests/unit/test_api_client.py:148-174` asserts the typed client hits the authorized task routes. Direct backend: `C:/Users/Acdev/RiderProjects/ActaskBack/tests/test_cli_v1_authorization.py:83-94` asserts `200` for member task query. | ✅ PASS |
| AC-04 | Revoked session fails as unauthenticated and can be replaced by a new login. | `tests/unit/test_auth_commands.py:159-182` asserts revoked `whoami` exits `3`, clears the stored credential, and a new login restores the session without echoing password/token. | ✅ PASS |
| AC-05 | Every read command has semantically equivalent human and JSON output. | `tests/unit/test_auth_commands.py:119-133` (`whoami`); `tests/unit/test_project_commands.py:64-83` (`projects list`); `tests/unit/test_project_commands.py:98-115` (`projects show`); `tests/unit/test_task_commands.py:80-126` (`tasks list`); `tests/unit/test_task_commands.py:149-167` (`tasks show`). | ✅ PASS |
| AC-06 | Write `--dry-run` does not mutate the server and reports normalized payload. | `tests/unit/test_task_commands.py:273-306` asserts `tasks create --dry-run --json` returns the normalized payload and never mutates; `tests/unit/test_task_commands.py:309-350` asserts `tasks update --dry-run --json` returns the normalized payload and fails if a network client is constructed. Scratch sensor below also kills an update dry-run fault. | ✅ PASS |
| AC-07 | The Skill completes read scenarios using only the CLI and stops safely on `401`, `403`, and destructive ambiguity. | `tests/skill/test_skill_forward_workflows.py:66-76` asserts CLI-only guidance and mandatory stops for `401`/`403`; `tests/skill/test_skill_forward_workflows.py:79-89` exercises `whoami --json`; `tests/skill/test_skill_forward_workflows.py:92-114` asserts dry-run-only write preview; `tests/skill/test_skill_forward_workflows.py:118-126` asserts forbidden read stops with exit code `4`; official validator returned `Skill is valid!`. | ✅ PASS |
| AC-08 | Native release binaries smoke-test on supported platforms and publish checksums. | GitHub Actions run `29120601408` completed successfully; release `v1.0.0` contains `actask-windows-x64.exe`, `actask-linux-x64`, `actask-macos-x64`, `actask-macos-arm64`, and `SHA256SUMS`. | ✅ PASS |

**Status**: AC-01..AC-08 = **8/8 PASS**.

---

## Gate Check

- **CLI test gate**: `C:\Users\Acdev\RiderProjects\ActaskCLI\.venv\Scripts\python.exe -m pytest -q`
  - Result: **52 passed** in 1.64s
- **Ruff**: `C:\Users\Acdev\RiderProjects\ActaskCLI\.venv\Scripts\python.exe -m ruff check .`
  - Result: **PASS**
- **Mypy**: `C:\Users\Acdev\RiderProjects\ActaskCLI\.venv\Scripts\python.exe -m mypy`
  - Result: **PASS** - `Success: no issues found in 14 source files`
- **Build**: `C:\Users\Acdev\RiderProjects\ActaskCLI\.venv\Scripts\python.exe -m build`
  - Result: **PASS** - built `actask_cli-1.0.0.tar.gz` and `actask_cli-1.0.0-py3-none-any.whl`
- **Skill validator**: `py -3.12 C:\Users\Acdev\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills/actask-cli`
  - Result: **PASS** - `Skill is valid!`
- **Direct backend test**: `C:\Users\Acdev\RiderProjects\ActaskBack\.venv\Scripts\python.exe -m pytest tests\test_cli_v1_authorization.py -q`
  - Result: **PASS** - `6 passed` in 2.11s
  - Notes: warnings only (Pydantic/`utcnow` deprecations in backend), no failures
- **Diff hygiene**: `git diff --check 26e0202..HEAD`
  - Result: **PASS**

**Test integrity**:

- `git ls-tree -r --name-only 26e0202 tests` returned no files.
- Current CLI tree collects **52 tests** under `tests/`.
- No evidence of deleted or weakened tests in `26e0202..HEAD`; `a319b55` increases coverage.

---

## Discrimination Sensor

Scratch state used a temporary detached `git worktree`; the real worktree was not modified.

| Mutation | File:line | Description | Targeted test | Killed? |
| --- | --- | --- | --- | --- |
| 1 | `src/actask_cli/commands/tasks.py:155` | Replaced update-path `if dry_run:` with `if False:` | `tests/unit/test_task_commands.py -q -k update_dry_run` | ✅ Killed - mutated run failed with `assert result.exit_code == 0`, proving the update dry-run test detects loss of dry-run behavior |
| 2 | `src/actask_cli/client/api.py:180` | Remapped HTTP `403` to `UnauthenticatedError` instead of `ForbiddenError` | `tests/unit/test_api_client.py -q -k maps_http_errors` | ✅ Killed - mutated run failed on `test_client_maps_http_errors_to_stable_exit_codes[403-ForbiddenError-4]` |

**Sensor depth**: lightweight, targeted to the two risks requested (`update --dry-run` and `403`).  
**Result**: **2/2 killed - PASS**

---

## Edge Cases

- [x] Revoked session is removed and replaced by fresh login (`tests/unit/test_auth_commands.py:159-182`)
- [x] Missing session remains distinct from forbidden access in direct backend checks (`C:/Users/Acdev/RiderProjects/ActaskBack/tests/test_cli_v1_authorization.py:76-108`)
- [x] Dry-run write path returns normalized payload and avoids network creation (`tests/unit/test_task_commands.py:273-350`)
- [x] Skill stops on forbidden access and does not proceed destructively (`tests/skill/test_skill_forward_workflows.py:92-126`)

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code / surgical diff | ✅ |
| No unrelated scope creep | ✅ |
| Matches local patterns/style | ✅ |
| Spec-anchored assertions target the promised outcomes | ✅ |
| Per-layer coverage expectation met for local scope | ✅ |
| Every test cited maps to a spec AC or gate concern | ✅ |
| Documented guidance followed: `AGENTS.md`, `.specs/features/cli-v1/tasks.md`, `C:\Users\Acdev\.codex\skills\tlc-spec-driven\references\validate.md` | ✅ |

---

## Summary

**What is verified locally**:

- CLI security, auth, authorization, read commands, write dry-run behavior, Skill safety flows, packaging, lint, typing, and build
- Direct backend authorization evidence for `200`, `401`, and `403`
- Discrimination sensor for both requested risk areas

**Release conclusion**:

- **The private `v1.0.0` release is complete.**
- **All acceptance criteria are verified, including native binaries and checksums.**
