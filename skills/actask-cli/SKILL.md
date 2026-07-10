---
name: actask-cli
description: Operate Actask projects and tasks through the public Actask CLI with individual user authentication and backend-enforced permissions. Use when an AI agent needs to inspect projects or tasks, create or update a task safely, interpret CLI JSON output, or stop safely on authentication, authorization, or destructive-action ambiguity.
---

# Actask CLI

Use only the installed `actask` command. Do not call the Actask API, database, browser, or credential store directly.

Before operating, require a globally available `actask` command. For normal use, install the release binary in the system PATH or run `pipx ensurepath` followed by `pipx install ...`; do not create a project-local virtual environment merely to operate Actask.

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

## Write Workflow

1. Read the relevant project and task state first.
2. State the proposed change, including task ID and changed fields, and obtain explicit user authorization unless the request already clearly authorizes that exact change.
3. Run `actask tasks create ... --dry-run --json` or `actask tasks update ... --dry-run --json`.
4. Compare the normalized dry-run payload with the authorized change. Ask again if fields, target, or effect differ.
5. Execute the matching command with `--yes --json` only after confirmation. Do not add commands for deletion or other destructive operations.

## Required Stops

- Exit code `3` / `401`: stop. Tell the user to run `actask login`; do not retry with another identity or credential.
- Exit code `4` / `403`: stop. State that the backend denied the action; do not probe IDs, filter locally, or attempt a bypass.
- Exit code `2`, `5`, `6`, or `7`: stop before a write. Explain the non-sensitive error and ask for corrected input or a later retry.
- Any destructive, ambiguous, broad, or irreversible request: do not execute it. Ask the user to clarify the exact target and intended effect.

Never expose credentials in prompts, output, examples, logs, fixtures, command-line arguments, or commits. The backend, not this Skill, decides authorization for every request.
