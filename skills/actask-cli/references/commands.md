# Actask CLI Command Reference

Use this reference with the `actask-cli` Skill. All identifiers below are placeholders; discover real IDs through authorized list commands.

## Output and exits

Data commands support `--json` and return this envelope on stdout:

```json
{"data": {}, "meta": {"request_id": null}, "error": null}
```

Diagnostics go to stderr. Exit codes: `0` success, `2` invalid input, `3` not authenticated, `4` forbidden, `5` not found, `6` conflict or invalid state, and `7` network or server failure.

## Session

```text
actask login
actask logout
actask whoami --json
actask version
```

`login` is interactive. The user enters the server URL, email, and hidden password locally. Never provide credentials to the agent or put them in a command argument.

## Projects

```text
actask projects list --json [--page <number>] [--page-size <number>]
actask projects show <project-id> --json
```

The list includes only backend-authorized projects. Project list pagination is local display pagination because the current backend route returns the authorized list without page parameters.

## Tasks

```text
actask tasks list --project <project-id> --json [--page <number>] [--page-size <number>] [--query <text>] [--filter <field:operator:value>]
actask tasks show <task-id> --json
```

Use filters exactly as `field:operator:value`. A `403` means access was denied; do not interpret it as an empty result.

## Safe writes

```text
actask tasks create --project <project-id> --title <title> --sprint <number> --dry-run --json
actask tasks create --project <project-id> --title <title> --sprint <number> --yes --json
actask tasks update <task-id> --title <title> --dry-run --json
actask tasks update <task-id> --title <title> --yes --json
```

Optional create and update fields are `--description`, `--column-id`, `--assignee-id`, `--priority`, and `--issue-type`. Read current state, dry-run, and obtain explicit confirmation before executing a write. `--dry-run` does not send a request.
