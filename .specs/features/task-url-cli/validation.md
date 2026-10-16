# Task URLs in the Actask CLI Validation

**Date:** 2026-10-16  
**Spec:** `.specs/features/task-url-cli/spec.md`  
**Branch:** `codex/task-url-cli`  
**Verifier:** implementation self-check, then an independent fresh-eyes pass with mutations in temporary worktrees (see "Independent Verification")

## Spec-Anchored Acceptance Criteria

| Criterion | Evidence | Result |
| --- | --- | --- |
| TU-001 | `test_task_commands.py::test_task_commands_accept_web_url_in_place_of_task_id` (show, promote, `create --parent-id`); `test_grouping_commands.py::test_group_accepts_web_urls_and_detects_url_id_duplicates`; `test_task_refs.py` passthrough of IDs and keys | ✅ PASS |
| TU-002 | `test_task_refs.py::test_parse_task_reference_rejects_urls_without_a_task`; `test_task_commands.py::test_task_commands_reject_web_url_without_task_before_request` (exit `2`, no request) | ✅ PASS |
| TU-003 | `test_grouping_commands.py::test_group_accepts_web_urls_and_detects_url_id_duplicates` (parent ID vs. child URL rejected before network) | ✅ PASS |
| TU-004 | `test_task_commands.py::test_tasks_url_prints_web_link_for_id_or_url` | ✅ PASS |
| TU-005 | `test_tasks_list_uses_backend_filters_and_has_equivalent_json`, `test_tasks_show_has_equivalent_human_and_json_output`, `test_tasks_promote_reads_responsibility_and_uses_official_command`, `test_tasks_url_requires_known_web_url_before_request` (`url` is `null`) | ✅ PASS |
| TU-006 | `test_profiles.py::test_profile_derives_web_url_for_official_servers`, `test_profile_store_persists_explicit_web_url_and_loads_legacy_profiles`; `test_auth_commands.py::test_login_asks_web_url_only_for_servers_without_a_known_web_app` and the unchanged default-server login transcript | ✅ PASS |
| TU-007 | `test_task_commands.py::test_tasks_url_requires_known_web_url_before_request` (exit `2`; the fake client would raise if it were called) | ✅ PASS |

## Independent Verification

The independent pass rated all TU criteria PASS and reported these findings, all fixed in the remediation commit:

| Finding | Fix | Evidence |
| --- | --- | --- |
| Medium: a decoded `task` value such as `..%2F..%2Fusers%2Fme` or `a%3Fx%3D1` reached the API path unencoded and could redirect the request | URL-derived IDs must match `[A-Za-z0-9_-]+`, otherwise exit `2` | `test_task_refs.py::test_parse_task_reference_rejects_ids_that_would_change_the_api_path` |
| Low: `host/tasks/all` without scheme and without `task=` was sent as an ID | Any value containing `/tasks` is parsed as a URL | `test_parse_task_reference_rejects_urls_without_a_task` |
| Low: `/tasksfoo` accepted as a task path | Path must be `/tasks` or start with `/tasks/` | same test |
| Low: re-login dropped the saved Web URL | The saved Web URL of the active profile is the prompt default | `test_auth_commands.py::test_login_asks_web_url_only_for_servers_without_a_known_web_app` |
| Low: extra login prompt not in release notes | Documented in `RELEASE_NOTES.md` | — |
| Surviving mutations (update, comments, cases, grouping children parsing; profile replace; first `task=`) | Added tests | `test_task_writes_and_task_children_accept_web_url`, `test_children_accepts_parent_web_url`, `test_parse_task_reference_uses_the_first_task_parameter`, profile replace in `test_profile_store_persists_explicit_web_url_and_loads_legacy_profiles` |

## Gate Check

- `python -m pytest -q`: **151 passed**, 0 failed.
- `python -m ruff check .`: **passed**.
- `python -m mypy`: **passed**, no issues in 16 source files.
- `python -m build`: **passed**, `actask_cli-1.2.0` sdist and wheel built.
- `git diff --check`: **passed**.

## Manual Check (production, read-only)

Using the existing session for `https://actaskapi.bluefronte.com`:

- `actask tasks list --project <EP> --page-size 1 --json` returned
  `url = https://actask.bluefronte.com/tasks/all?task=<uuid>`.
- `actask tasks url <uuid>` printed the same URL.
- `actask tasks show <that URL> --json` returned the same task (`EP-1`).
- `actask tasks url https://actask.bluefronte.com/tasks/all` exited `2` with
  `The task URL does not contain the 'task' parameter.`

Not verified: opening the link in a browser. The format matches
`ActaskFront/src/utils/taskLinks.js` and the backend `/tasks/{id}/redirect`.
