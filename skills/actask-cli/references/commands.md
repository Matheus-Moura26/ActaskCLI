# Actask CLI Command Reference

Use this reference with the `actask-cli` Skill. All identifiers below are placeholders; discover real IDs through authorized list commands.

## Output and exits

Data commands support `--json` and return this envelope on stdout:

```json
{"data": {}, "meta": {"request_id": null}, "error": null}
```

Diagnostics go to stderr. Exit codes: `0` success, `2` invalid input, `3` not authenticated, `4` forbidden, `5` not found, `6` conflict or invalid state, and `7` network/server failure or an API-contract incompatibility. A 405 is reported as a contract incompatibility, never as a successful read.

## Session

```text
actask login
actask logout
actask whoami --json
actask version
```

`login` is interactive. Its default server is `https://actaskapi.bluefronte.com`; the user can press Enter at Server URL to use it. The user enters the email and hidden password locally. Never provide credentials to the agent or put them in a command argument.

## Installation for agents and users

Require `actask` to resolve from the system PATH before operating. Use a release binary installed in a system PATH directory, or `pipx ensurepath` followed by `pipx install` for a globally callable per-user command. Do not create a project-local virtual environment for ordinary CLI operation; reserve `.venv` for CLI development and tests.

The official source is `https://github.com/Matheus-Moura26/ActaskCLI`. Do not install binaries from a fork. For release binaries, verify the SHA-256 against `SHA256SUMS` from the same official release before running `actask`.

## Projects

```text
actask projects list --json [--page <number>] [--page-size <number>]
actask projects show <project-id> --json
```

The list includes only backend-authorized projects. Project list pagination is local display pagination because the current backend route returns the authorized list without page parameters.

```text
actask projects columns <project-id> --json
actask projects fields <project-id> --json
```

Use `columns` to resolve a visual board-column name to its ID. Use `fields` to discover the actual configured Status field options and supported filters for that project.

## Tasks

```text
actask tasks list --project <project-id> --json [--page <number>] [--page-size <number>] [--query <text>] [--filter <field:operator:value>]
actask tasks show <task-id> --json
actask tasks create --project <project-id> --title <title> --sprint <number> --parent-id <parent-task-id> --dry-run --json
actask tasks cases list <task-id> --json
actask tasks cases fields <task-id> --json
actask tasks cases create <task-id> --description <text> --field-values <json-object> --dry-run --json
actask tasks cases update <task-id> <case-id> --field-values <json-object> --dry-run --json
```

Use filters exactly as `field:operator:value`. A `403` means access was denied; do not interpret it as an empty result.

For an exact board column, use `--filter column:=:<column-id>`. For an exact configured Status option, use `--filter status:=:<option-value>`. Do not assume that column names, Status options, and `statusCategory` mean the same thing.

For counts, request a filtered page and read `meta.total`; `data.length` is only the current page. For a complete list, request subsequent pages until the collected count reaches `meta.total`.

### Task assignee names

The task response keeps the stable `assignee_id` and includes the display field `assignee_name`:

```text
actask tasks show <task-id> --json
actask tasks list --project <project-id> --json
```

Read `data.assignee_name` for `tasks show` and `assignee_name` from each object in `data` for `tasks list`. In human-readable output, the columns are `key`, `title`, `project_id`, `task_id`, and `assignee_name`; the final column is empty when there is no assignee.

### Multiline descriptions

Use a UTF-8 file instead of an inline argument when a task or case description contains line breaks:

```text
actask tasks create --project <project-id> --title <title> --sprint <number> --description-file .\description.md --dry-run --json
actask tasks update <task-id> --description-file .\description.md --dry-run --json
actask tasks cases create <task-id> --description-file .\case-description.md --dry-run --json
actask tasks cases update <task-id> <case-id> --description-file .\case-description.md --dry-run --json
```

On macOS/Linux, use `./description.md` paths. To read from standard input, pass `--description-file -`, for example `cat description.md | actask tasks create ... --description-file -`. The file contents are read as UTF-8 inside the CLI. Do not pass `--description` and `--description-file` together.

## Safe writes

```text
actask tasks create --project <project-id> --title <title> --sprint <number> --dry-run --json
actask tasks create --project <project-id> --title <title> --sprint <number> --yes --json
actask tasks create --project <project-id> --title <title> --sprint <number> --parent-id <parent-task-id> --yes --json
actask tasks update <task-id> --title <title> --dry-run --json
actask tasks update <task-id> --title <title> --yes --json
```

Optional create fields are `--description`, `--column-id`, `--assignee-id`, `--priority`, `--issue-type`, and `--parent-id`. Supplying `--parent-id` creates a subtask under that parent. First inspect the parent with `tasks show`, copy its `project_id` into `--project`, and do not use a subtask as the parent: Actask supports one hierarchy level and the backend verifies this invariant. The remaining optional update fields are `--description`, `--column-id`, `--assignee-id`, `--priority`, and `--issue-type`. For `tasks update`, `--column-id` uses the canonical `PATCH /tasks/{id}/move` contract. Before sending it, the CLI reads only the authorized task and project columns (including their ordering revisions), then sends a protected zero-based `position` or `append_to_end` placement. The backend resolves the final order while holding its ordering locks; frontend clients that already send anchors remain supported. When `--position` is omitted, the task is appended to the end. The backend remains the authority for authorization and optimistic-concurrency validation. Do not combine `--column-id` with other update fields; run the move as a separate confirmed command to avoid a partially applied multi-request change. `--position` requires `--column-id`. Read current state, dry-run, and obtain explicit confirmation before executing a write. `--dry-run` does not send a request. If transport fails, the CLI reports the HTTP method, relative path, and safe exception type; it does not retry the move automatically.
Cases linked to a task use the following commands:

```text
actask tasks cases list <task-id> --json
actask tasks cases fields <task-id> --json
actask tasks cases create <task-id> [--description <text>] [--tenant-id <id>] [--person-id <id>] [--motivo <text>] [--solucao <text>] [--field-values <json-object>] --yes --json
actask tasks cases update <task-id> <case-id> [--description <text>] [--tenant-id <id>] [--person-id <id>] [--clear-person-ids] [--is-done true|false] [--motivo <text>] [--solucao <text>] [--field-values <json-object>] --yes --json
```

Use `cases list` to obtain the case ID and `cases fields` to discover the project-scoped field definition IDs, types and options. `--field-values` is a JSON object keyed by those definition IDs. Before a write, the CLI reads the task for the existing responsibility guard, reads the project's case-field definitions, validates text/number/select-single/select-multi values and then lets the backend enforce authorization and persistence. Case writes require `--dry-run` or confirmation, and `--yes` suppresses the prompt. There is no case deletion command in this workflow.

Task comments use the existing authorized comment routes:

```text
actask tasks comments list <task-id> --json
actask tasks comments create <task-id> --content <text> --dry-run --json
actask tasks comments create <task-id> --content <text> --mention-user-id <user-id> --yes --json
actask tasks comments create <task-id> --content <text> --mention-user-id <user-id> --parent-id <comment-id> --yes --json
```

Repeat `--mention-user-id` for multiple people. The backend also resolves exact `@label` mentions in the content; explicit IDs are recommended for deterministic automation. Comment creation reads the current identity and task first, applies the same responsibility guard as other existing-task writes, and then sends `POST /tasks/{task-id}/comments` with `content`, `mentioned_user_ids`, and optional `parent_id`. `--dry-run` does not create a session or send a request. There is no comment deletion command in this workflow.
