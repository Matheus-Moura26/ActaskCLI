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

For the official servers (`https://actaskapi<env>.<domain>`), the CLI derives the web app URL used for task links (`https://actask<env>.<domain>`). For any other server, `login` also asks for an optional `Web URL for task links`; leaving it empty disables task links for that profile.

## Installation for agents and users

Require `actask` to resolve from the system PATH before operating. Use a release binary installed in a system PATH directory, or `pipx ensurepath` followed by `pipx install` for a globally callable per-user command. Do not create a project-local virtual environment for ordinary CLI operation; reserve `.venv` for CLI development and tests.

The official source is `https://github.com/Matheus-Moura26/ActaskCLI`. Do not install binaries from a fork. For release binaries, verify the SHA-256 against `SHA256SUMS` from the same official release before running `actask`.

## Projects

```text
actask projects list --json [--page <number>] [--page-size <number>]
actask projects create --name <name> --key <key> [--current-sprint <number>] [--timezone <iana-zone>] --dry-run --json
actask projects create --name <name> --key <key> [--current-sprint <number>] [--timezone <iana-zone>] --yes --json
actask projects show <project-id> --json
```

The list includes only backend-authorized projects. Project list pagination is local display pagination because the current backend route returns the authorized list without page parameters.

Project creation sends `POST /projects` with `name`, `key`, `current_sprint`
(default `1`) and `timezone` (default `America/Sao_Paulo`). The CLI normalizes
the key to uppercase, requires the backend's global `createProjects` permission,
and never treats local validation as authorization. Use `--dry-run` to inspect
the normalized payload without a request; use `--yes` to suppress confirmation.

```text
actask projects columns <project-id> --json
actask projects fields <project-id> --json
```

Use `columns` to resolve a visual board-column name to its ID. Use `fields` to discover the actual configured Status field options and supported filters for that project.

## Tasks

```text
actask tasks list --project <project-id> --json [--page <number>] [--page-size <number>] [--query <text>] [--filter <field:operator:value>]
actask tasks show <task-id> --json
actask tasks url <task-id> --json
actask tasks create --project <project-id> --title <title> --sprint <number> --parent-id <parent-task-id> --dry-run --json
actask tasks promote <task-id> --dry-run --json
actask tasks promote <task-id> --yes --json
actask tasks cases list <task-id> --json
actask tasks cases fields <task-id> --json
actask tasks cases create <task-id> --description <text> --field-values <json-object> --dry-run --json
actask tasks cases update <task-id> <case-id> --field-values <json-object> --dry-run --json
```

Use filters exactly as `field:operator:value`. A `403` means access was denied; do not interpret it as an empty result.

### Task links

Every `<task-id>`, `<parent-task-id>`, `--parent-id` of `tasks create`, and the grouping `--parent`/`--child` options also accept the task web URL `https://<web-host>/tasks/all?task=<task-id>`. Other query parameters such as `comment` are ignored. A URL without a `task` parameter, or whose `task` value is not a plain ID (letters, digits, `-` and `_`), exits with code `2` before any request.

```text
actask tasks show "https://actask.bluefronte.com/tasks/all?task=<task-id>" --json
actask tasks url <task-id-or-url>
actask tasks url <task-id-or-url> --json
```

`tasks url` reads the task through the authorized route and prints only its link. Its JSON `data` is `{"id":"<task-id>","key":"<task-key>","url":"<task-url>"}`. The JSON `data` of `tasks show`, `tasks create`, `tasks update` and `tasks promote`, and each object of `tasks list`, include `url`; it is `null` when the profile has no known web URL. In that case `tasks url` exits with code `2` and asks the user to run `actask login` and provide the Web URL.

For an exact board column, use `--filter column:=:<column-id>`. For an exact configured Status option, use `--filter status:=:<option-value>`. Do not assume that column names, Status options, and `statusCategory` mean the same thing.

For counts, request a filtered page and read `meta.total`; `data.length` is only the current page. For a complete list, request subsequent pages until the collected count reaches `meta.total`.

### Task assignee names

The task response keeps the stable `assignee_id` and includes the display field `assignee_name`:

```text
actask tasks show <task-id> --json
actask tasks list --project <project-id> --json
```

Read `data.assignee_name` for `tasks show` and `assignee_name` from each object in `data` for `tasks list`. In human-readable output, the columns are `key`, `title`, `project_id`, `task_id`, `assignee_name`, and `url`; `assignee_name` is empty when there is no assignee and `url` is empty when the web URL is unknown.

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
actask tasks promote <task-id> --dry-run --json
actask tasks promote <task-id> --yes --json
```

Optional create fields are `--description`, `--column-id`, `--assignee-id`, `--priority`, `--issue-type`, and `--parent-id`. Supplying `--parent-id` creates a subtask under that parent. First inspect the parent with `tasks show`, copy its `project_id` into `--project`, and do not use a subtask as the parent: Actask supports one hierarchy level and the backend verifies this invariant. The remaining optional update fields are `--description`, `--column-id`, `--assignee-id`, `--priority`, and `--issue-type`. For `tasks update`, `--column-id` uses the canonical `PATCH /tasks/{id}/move` contract. Before sending it, the CLI reads only the authorized task and project columns (including their ordering revisions), then sends a protected zero-based `position` or `append_to_end` placement. The backend resolves the final order while holding its ordering locks; frontend clients that already send anchors remain supported. When `--position` is omitted, the task is appended to the end. The backend remains the authority for authorization and optimistic-concurrency validation. Do not combine `--column-id` with other update fields; run the move as a separate confirmed command to avoid a partially applied multi-request change. `--position` requires `--column-id`. Read current state, dry-run, and obtain explicit confirmation before executing a write. `--dry-run` does not send a request. If transport fails, the CLI reports the HTTP method, relative path, and safe exception type; it does not retry the move automatically.
### Promote a standard subtask

`tasks promote` is the official way to turn a standard subtask into a normal
task. It clears only `parent_id` and keeps the task identity and content. Read
the current identity and task first, then review the no-network dry-run and
execute the matching confirmed command:

```text
actask whoami --json
actask tasks show <task-id> --json
actask tasks promote <task-id> --dry-run --json
actask tasks promote <task-id> --yes --json
```

The dry-run `data` is:

```json
{"operation":"promote_subtask","task_id":"<task-id>","parent_id":null}
```

The command applies the same responsibility guard as other writes to an
existing task: it stops with exit code `4` when another user is responsible.
The backend is the final authority. A custom subtask, identified by a non-null
`custom_subtask_definition_id`, is rejected with conflict exit code `6` because
this flow must not discard or detach custom field values. Repeating promotion
for an already-normal standard task is idempotent and does not add duplicate
history or automation events.

## Task grouping

Grouping is independent from standard subtasks. It sets `grouping_parent_id`
on an existing root task, never `parent_id`; grouped tasks are hidden from
project-board columns and remain available in the parent's **Agrupadas**
section. The parent stays visible. `isGroupingTask`/`is_grouping_task` identifies
a parent with active grouped children, and `isGroupedTask`/`is_grouped_task`
identifies a task that belongs to a grouping parent.

Create the parent first with the normal task command when necessary. Do not use
`--parent-id` for a grouping parent:

```text
actask tasks create --project <project-id> --title <title> --sprint <number> --dry-run --json
actask tasks create --project <project-id> --title <title> --sprint <number> --yes --json
```

Discover eligible root tasks and their flags with:

```text
actask tasks grouping candidates --project <project-id> --json
actask tasks grouping candidates --project <project-id> --query <text> --page 1 --page-size 100 --json
```

Group an existing parent with one or more existing child IDs or exact public
keys. Repeat `--child`; the CLI reads the parent and every child before
confirmation, resolves public keys within the authorized project, and sends
only IDs to the backend while
the backend performs the final project, root-task, conflict and permission
checks atomically:

```text
actask tasks grouping group --project <project-id> --parent <parent-task-id> \
  --child <child-task-id> --child <another-child-task-id> \
  --idempotency-key <key> --dry-run --json
actask tasks grouping group --project <project-id> --parent <parent-task-id> \
  --child <child-task-id> --child <another-child-task-id> \
  --idempotency-key <key> --yes --json
```

`create` is an alias for `group`; `--request-id` is an alias for
`--idempotency-key`. The grouping mutation requires project access and
`moveTasks`, except for master users. A retry with the same idempotency key
returns the same operation instead of creating a second log entry.

Inspect the operation log, grouped children, and undo a specific operation:

```text
actask tasks grouping list --project <project-id> --status active --page 1 --page-size 50 --json
actask tasks grouping log --project <project-id> --json
actask tasks grouping children <parent-task-id> --json
actask tasks grouping undo --project <project-id> --operation-id <operation-id> --dry-run --json
actask tasks grouping undo --project <project-id> --operation-id <operation-id> --yes --json
```

`undo` is atomic and audited; it removes the relationships from that operation
without deleting or changing task content. The operation ID comes from
`group` or the log, and a repeated undo is idempotent. Use the normal task
filters to find parents or grouped children:

```text
actask tasks list --project <project-id> --filter isGroupingTask:equals:true --json
actask tasks list --project <project-id> --filter isGroupedTask:equals:true --json
```

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
