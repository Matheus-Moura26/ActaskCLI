# Task URLs in the Actask CLI

**Status:** Implemented

## Goal

Let a user or an AI agent paste a task's Actask web URL wherever the CLI takes
a task ID, and let the CLI report the web URL of a task.

## Context

The web app opens a task with `https://<web-host>/tasks/all?task=<task-id>`
(`ActaskFront/src/utils/taskLinks.js`, `buildTaskUrl`). The backend builds the
same link in `GET /tasks/{task_id}/redirect` from `FRONTEND_URL`. The link always
uses the task UUID `id`, never the public `key`. The API and web app live on
different hosts (`actaskapi.bluefronte.com` serves `actask.bluefronte.com`).

## Requirements

- **TU-001:** Every task-ID argument accepts a task web URL and uses its `task`
  query parameter as the task ID. This covers `tasks show`, `update`,
  `promote`, `comments list/create`, `cases list/fields/create/update`,
  `tasks create --parent-id`, `tasks grouping children` and grouping
  `--parent`/`--child`. Plain IDs and grouping public keys keep working.
- **TU-002:** A URL that is not an Actask task URL, or that has no `task`
  parameter, exits with code `2` before any network request. The URL host is not
  checked; the backend remains the authorization authority.
- **TU-003:** Grouping normalizes URLs before its duplicate and parent/child
  checks, so a URL and the ID of the same task are detected as the same task.
- **TU-004:** `actask tasks url <task-id-or-url> [--json]` reads the task through
  `GET /tasks/{task_id}` and prints its web URL. Its JSON `data` is
  `{"id", "key", "url"}`.
- **TU-005:** The JSON `data` of `tasks show`, `create`, `update`, `promote` and
  each `tasks list` item includes `url`, computed locally (`null` when the web URL
  is unknown). Human output appends `url` as the last tab-separated column.
- **TU-006:** The web URL is derived for official servers
  (`actaskapi<env>.<domain>` → `actask<env>.<domain>`). For other servers,
  `login` asks for an optional `Web URL for task links`, stored in the profile.
  Existing profiles load unchanged; credentials stay keyed by server and email.
- **TU-007:** `tasks url` exits with code `2` and points to `actask login` when
  the web URL is unknown, before any network request.

## Out of scope

- Resolving public keys such as `MMS-152` outside grouping.
- Using the URL `comment` parameter.

## Verification

- `tests/unit/test_task_refs.py`: URL parsing and link building.
- `tests/unit/test_profiles.py`: derivation, persistence and legacy profiles.
- `tests/unit/test_auth_commands.py`: Web URL prompt only for custom servers.
- `tests/unit/test_task_commands.py` and `test_grouping_commands.py`: URL input,
  `tasks url`, `url` in outputs and URL/ID duplicate detection.
- `tests/skill/test_skill_forward_workflows.py`: Skill and reference guidance.
