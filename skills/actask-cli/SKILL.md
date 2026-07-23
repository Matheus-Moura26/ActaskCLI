---
name: actask-cli
description: Operate Actask projects and tasks through the public Actask CLI with individual user authentication and backend-enforced permissions. Use when an AI agent needs to inspect projects or tasks, create or update a task safely, interpret CLI JSON output, or stop safely on authentication, authorization, or destructive-action ambiguity.
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
2. State the proposed change, including task ID and changed fields, and obtain explicit user authorization unless the request already clearly authorizes that exact change.
3. Run `actask tasks create ... --dry-run --json` or `actask tasks update ... --dry-run --json`.
4. Compare the normalized dry-run payload with the authorized change. Ask again if fields, target, or effect differ.
5. Execute the matching command with `--yes --json` only after confirmation. Do not add commands for deletion or other destructive operations.

## Required Stops

- Exit code `3` / `401`: stop. Tell the user to run `actask login`; do not retry with another identity or credential.
- Exit code `4` / `403`: stop. State that the backend denied the action; do not probe IDs, filter locally, or attempt a bypass.
- Exit code `2`, `5`, `6`, or `7`: stop before a write. Explain the non-sensitive error and ask for corrected input or a later retry. In particular, code `7` can mean either network/server failure or an API-contract incompatibility (such as HTTP 405); do not misrepresent it as a successful read or retry it as a write.
- Any destructive, ambiguous, broad, or irreversible request: do not execute it. Ask the user to clarify the exact target and intended effect.

Never expose credentials in prompts, output, examples, logs, fixtures, command-line arguments, or commits. The backend, not this Skill, decides authorization for every request.
