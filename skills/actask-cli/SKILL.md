---
name: actask-cli
description: Operate Actask projects and tasks through the public Actask CLI with individual user authentication and backend-enforced permissions. Use when an AI agent needs to inspect projects or tasks, create or update a task safely, group or ungroup tasks, interpret CLI JSON output, or stop safely on authentication, authorization, or destructive-action ambiguity.
---

# Actask CLI

Use only the installed `actask` command. Do not call the Actask API, database, browser, or credential store directly.

Before operating, require a globally available `actask` command. For normal use, install the release binary in the system PATH or run `pipx ensurepath` followed by `pipx install ...`; do not create a project-local virtual environment merely to operate Actask.

Trust releases only from `https://github.com/Matheus-Moura26/ActaskCLI`. A fork or third-party binary is not an official distribution. When installing a release binary, verify it against `SHA256SUMS` from the same official release before execution. Never disable or skip an integrity mismatch.

Read [references/commands.md](references/commands.md) before choosing command flags or interpreting output.

## Identity and Discovery

1. Ask the user to run `actask login` themselves if a session is absent or invalid. Do not request, accept, print, store, paste, or relay a password, API token, session token, or authentication header.
2. Start each operation with `actask whoami --json`. Treat its identity as the only current user identity.
3. Discover project and task IDs with authorized list commands. Never invent IDs or reuse IDs from another user or server profile.
4. Use `--json` for data commands. Parse the `data`, `meta`, and `error` envelope; retain request IDs only for diagnostics.

## Read Workflow

1. Run `actask projects list --json` to discover accessible projects.
2. Run `actask projects show <project-id> --json` before working in a selected project when context matters.
3. Run `actask tasks list --project <project-id> --json` to discover tasks. Use only documented filters.
4. Run `actask tasks show <task-id> --json` to inspect one task.
5. Summarize only returned data. Do not infer access to projects or tasks that are not returned.

## Task Assignee Names

Task responses preserve `assignee_id` as the stable identifier and expose `assignee_name` as the display name. When a task is unassigned, `assignee_id` and `assignee_name` are `null`.

1. For one task, run `actask tasks show <task-id> --json` and read `data.assignee_name`.
2. For a task list, run `actask tasks list --project <project-id> --json` and read `assignee_name` from each object in `data`.
3. Prefer `--json` for automation. In human-readable task output, the fifth tab-separated field is `assignee_name`; an empty field means that the task is unassigned.
4. Never derive a person's name from `assignee_id` or make a separate user lookup when `assignee_name` is present in the task response.

## Multiline Descriptions

Use `--description-file <path>` for task or case descriptions that contain line breaks. The CLI reads the file as UTF-8 inside the process, so the content is not exposed to shell or batch-file argument parsing.

1. For Windows PowerShell, use a path such as `--description-file .\description.md`.
2. For macOS/Linux, use a path such as `--description-file ./description.md`.
3. Use `--description-file -` to read the description from stdin, for example `Get-Content -Raw .\description.md | actask tasks create ... --description-file -` or `cat description.md | actask tasks create ... --description-file -`.
4. Do not combine `--description` and `--description-file`; the CLI exits with invalid input before making a request.
5. The file option is available for `tasks create`, `tasks update`, `tasks cases create`, and `tasks cases update`.

## Task Grouping

Task grouping is a separate relationship from standard subtasks. A grouped task
keeps its existing content and has `grouping_parent_id` set to the grouping
parent; it does not use `parent_id`. Grouped tasks are hidden from project-board
columns and are exposed through the parent's **Agrupadas** section. The parent
remains a normal root task on the board. `is_grouping_task`/`isGroupingTask`
means that a task has at least one active grouped child, while
`is_grouped_task`/`isGroupedTask` means that the task belongs to a grouping
parent.

Use only the public CLI commands below; do not call the API or the backend's
database script directly:

1. Run `actask whoami --json`, discover the project with `actask projects list --json`, and inspect available tasks with `actask tasks grouping candidates --project <project-id> --json`.
2. If a new parent is needed, create it first with `actask tasks create --project <project-id> ...` without `--parent-id`. A parent must be an existing root task before grouping.
3. Preview the relationship without a request: `actask tasks grouping group --project <project-id> --parent <parent-id-or-key> --child <child-id-or-key> --child <another-child-id-or-key> --dry-run --json`.
4. After confirming the exact parent and child IDs or public keys, execute the same command with `--yes --json`. Repeat `--child` for each grouped task. Use `--idempotency-key <key>` when a retry must refer to the same batch; on a real run the CLI resolves public keys to IDs inside the authorized project.
5. Review the audit log with `actask tasks grouping list --project <project-id> --json` (or the `log` alias), and inspect hidden children with `actask tasks grouping children <parent-task-id> --json`.
6. Undo only a specific operation from that log. Preview with `actask tasks grouping undo --project <project-id> --operation-id <operation-id> --dry-run --json`, then execute with `--yes --json` after explicit confirmation. Undo is an atomic, audited operation and is not task deletion.

Grouping mutations are project-level operations. The backend requires project
access plus `moveTasks` (or master access); the CLI must never infer or bypass
that authorization. The command reads the selected tasks before confirmation,
but the backend remains the final authority and may reject a stale, grouped,
archived, subtask, cross-project, duplicate, or otherwise invalid selection.
For filters, use the system field keys with the normal task-list syntax:
`actask tasks list --project <project-id> --filter isGroupingTask:equals:true --json`
and `--filter isGroupedTask:equals:true`.

## Ambiguous Counts And Lists

1. Treat terms such as "pendentes", "abertas", "em andamento" and "status" as ambiguous unless the user identifies a column or a configured field option.
2. Discover the real project configuration with `actask projects columns <project-id> --json` and `actask projects fields <project-id> --json`.
3. When more than one real interpretation matches, present the matching project column names and configured Status options, then ask the user which one to use. Do not invent `todo`, `in_progress`, or any other value.
4. When the user says "na coluna X", resolve X to one exact project column and query with `--filter column:=:<column-id>`.
5. When the user says "com Status X", resolve X to one exact configured Status option and query with `--filter status:=:<option-value>`.
6. For a count, use `meta.total` from the filtered backend query. Never derive a total from `data.length`.
7. For a list or analysis of every matching task, paginate until collected items equal `meta.total`. If a page fails, report a partial result and do not use words such as "total", "only" or "all".
8. Keep `column`, `status`, and `statusCategory` distinct. Only use a status category when the user explicitly asks for that field.
9. Stop on `401` or `403`; do not use list data as a fallback for a denied detail request.

## Write Workflow

1. Read the relevant project and task state first.
2. Before creating a subtask, read its intended parent with `actask tasks show <parent-task-id> --json`; use the parent's `project_id` and do not create a child of another subtask. The backend enforces the one-level hierarchy.
3. State the proposed change, including task ID and changed fields, and obtain explicit user authorization unless the request already clearly authorizes that exact change.
4. Run `actask tasks create ... --dry-run --json` or `actask tasks update ... --dry-run --json`.
5. Compare the normalized dry-run payload with the authorized change. Ask again if fields, target, or effect differ.
6. Execute the matching command with `--yes --json` only after confirmation. Do not add commands for deletion or other destructive operations.

### Responsibility guard for existing tasks

Before any write that changes an existing task (`tasks update`,
`tasks cases create`, `tasks cases update`, or `tasks comments create`), read the current identity and
the task's current `assignee_id`. The CLI may proceed only when the task is
unassigned or the authenticated user's ID matches `assignee_id`. If another
user is responsible, stop before the write with exit code `4` and the exact
message `Você não é o responsável desta task`. This is a CLI-side business
rule; the backend remains the final authorization authority. `tasks create` is
not subject to this guard because it creates a new task with no existing
responsible user.

`tasks grouping group` and `tasks grouping undo` are project-level mutations,
not ordinary task-field updates. They use the grouping contract and the
backend's `moveTasks`/master authorization; do not replace that check with an
assignee lookup or attempt to bypass a `403`.

For cases linked to a task, use `actask tasks cases list <task-id> --json` to obtain case IDs and `actask tasks cases fields <task-id> --json` to obtain the project's field definition IDs, types and options. Use `actask tasks cases create` or `actask tasks cases update` with `--field-values <json-object>` for custom case fields. These writes read the task first, apply the same responsibility guard as other task writes, validate configured field types/options locally, and then rely on the backend for authorization and persistence. Use `--dry-run` before a write and `--yes --json` only after the normalized payload is confirmed.

For an ordered move, use `actask tasks update <task-id> --column-id <column-id> [--position <zero-based-index>]`. The CLI resolves the authorized task and project-column ordering revisions, then sends a protected position-based move request; the backend resolves the final order while holding its ordering locks. Omit `--position` to append to the target column. The backend still validates authorization and concurrency; the CLI must not call the API directly or attempt to reorder tasks with a `PUT` update. Transport failures report the method, relative path, and safe exception type without exposing credentials, and the CLI does not retry a move automatically.

For comments linked to a task, use `actask tasks comments list <task-id> --json` to inspect existing comments. Create a comment with `actask tasks comments create <task-id> --content <text> --mention-user-id <user-id> --dry-run --json`; repeat `--mention-user-id` for multiple people and use `--parent-id` for a reply. The backend can also resolve exact `@label` mentions in the content, but explicit user IDs are preferred for deterministic automation. Comment creation reads the task responsibility guard before writing, supports `--yes --json` after the dry-run is confirmed, and does not expose any delete operation.

## Required Stops

- Exit code `3` / `401`: stop. Tell the user to run `actask login`; do not retry with another identity or credential.
- Exit code `4` / `403`: stop. State that the backend denied the action; do not probe IDs, filter locally, or attempt a bypass.
- Exit code `2`, `5`, `6`, or `7`: stop before a write. Explain the non-sensitive error and ask for corrected input or a later retry. In particular, code `7` can mean either network/server failure or an API-contract incompatibility (such as HTTP 405); do not misrepresent it as a successful read or retry it as a write.
- Any destructive, ambiguous, broad, or irreversible request: do not execute it. Ask the user to clarify the exact target and intended effect.

Never expose credentials in prompts, output, examples, logs, fixtures, command-line arguments, or commits. The backend, not this Skill, decides authorization for every request.
