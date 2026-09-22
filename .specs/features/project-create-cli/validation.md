# Project Creation in the Actask CLI Validation

**Date:** 2026-09-22  
**Spec:** `.specs/features/project-create-cli/spec.md`  
**Diff:** `HEAD` (feature commit)  
**Verifier:** standalone fresh-eyes pass; behavior mutations were executed in temporary worktrees

## Spec-Anchored Acceptance Criteria

| Criterion | Spec-defined outcome | Evidence | Result |
| --- | --- | --- | --- |
| PC-001 | Authenticated `POST /projects` with all project fields | `tests/unit/test_api_client.py:231` — `assert [(request.method, request.url.path) for request in requests] == [("POST", "/projects")]`; `:234` — `assert json.loads(requests[0].content) == {...}` | ✅ PASS |
| PC-002 | Required name/key and defaults `current_sprint=1`, `timezone=America/Sao_Paulo` | `tests/unit/test_project_commands.py:186` — `assert json.loads(result.output) == {... "current_sprint": 1, ... "timezone": "America/Sao_Paulo" ...}`; `:252` — `assert result.exit_code == 2` | ✅ PASS |
| PC-003 | Project key is normalized to uppercase | `tests/unit/test_project_commands.py:157` — `assert client.created_payload == {... "key": "NEW", ...}`; `:186` — dry-run asserts `"key": "NEW"` | ✅ PASS |
| PC-004 | Confirmation/`--yes`; dry-run makes no network client | `tests/unit/test_project_commands.py:185` — `assert result.exit_code == 0`; `:239` — `assert client.created_payload is None` after cancellation; `:186` — dry-run output assertion | ✅ PASS |
| PC-005 | Human and JSON success outputs represent the same project | `tests/unit/test_project_commands.py:150` — `assert human.output == "EX\tExample Project\tproject-1\n"`; `:152` — `assert payload == {"data": PROJECT_ONE.to_data(), ...}` | ✅ PASS |
| PC-006 | Backend authorization remains authoritative and `403` is preserved | `tests/unit/test_project_commands.py:215` — `assert result.exit_code == 4`; `:216` — `assert result.stderr == "You do not have permission to perform this action.\n"`; `tests/unit/test_api_client.py:149` — `assert error.value.exit_code == exit_code` for the `401`/`403` matrix | ✅ PASS |

## Edge Cases

- ✅ Empty project name is rejected with exit code `2` and no client mutation (`tests/unit/test_project_commands.py:252-254`).
- ✅ Confirmation cancellation returns success without calling project creation (`tests/unit/test_project_commands.py:237-239`).
- ✅ Forbidden backend response remains exit code `4` (`tests/unit/test_project_commands.py:215-216`).

## Gate Check

- `python -m pytest -q`: **112 passed**, 0 failed.
- `python -m ruff check .`: **passed**.
- `python -m mypy`: **passed**, no issues in 15 source files.
- `python -m build`: **passed**, sdist and wheel built.
- Skill validator: **passed**, `Skill is valid!`.
- `git diff --check`: **passed**.

## Discrimination Sensor

| Mutation | Result |
| --- | --- |
| Removed `.upper()` from project-key normalization in `projects.py` | ✅ Killed: 2 project-create tests failed. |
| Changed `create_project` transport from `POST` to `GET` in `api.py` | ✅ Killed: the authorized-route contract test failed. |

**Sensor:** 2/2 mutations killed — ✅ PASS.

## Code Quality

- ✅ Changes are scoped to the typed client, project command, tests, documentation and feature evidence.
- ✅ Existing backend authorization is reused; no local permission bypass was added.
- ✅ No credentials were added to arguments, output, fixtures or logs.
- ✅ Human/JSON output, confirmation and dry-run follow existing CLI patterns.

## Verdict

**Overall:** ✅ Ready. The project creation command is implemented, tested,
documented and ready for release when authorized.
