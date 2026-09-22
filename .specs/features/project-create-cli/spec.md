# Project Creation in the Actask CLI

**Status:** Implemented

## Goal

Allow an authenticated user to create an Actask project from the CLI through
the backend's existing protected project-creation route.

## Requirements

- **PC-001:** `actask projects create` sends `POST /projects` with `name`,
  `key`, `current_sprint` and `timezone`.
- **PC-002:** `name` and `key` are required; `current_sprint` defaults to `1`
  and `timezone` defaults to `America/Sao_Paulo`.
- **PC-003:** The CLI normalizes the project key to uppercase before showing or
  sending the payload.
- **PC-004:** Creation requires confirmation or `--yes`; `--dry-run` returns
  the normalized payload without constructing a network client.
- **PC-005:** Successful creation supports equivalent human and `--json`
  output using the stable `data`, `meta`, and `error` envelope.
- **PC-006:** Backend `401` and `403` responses remain distinct CLI errors; the
  CLI does not infer or bypass the backend's `createProjects` authorization.

## Verification

- `tests/unit/test_project_commands.py` covers normalized output, dry-run,
  confirmation, invalid input and forbidden responses.
- `tests/unit/test_api_client.py` covers the authenticated `POST /projects`
  request and typed project response.
