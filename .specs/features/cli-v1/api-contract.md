# Actask CLI v1 API Contract

**Version:** backend contract observed on 2026-07-10
**Authentication:** protected requests send `X-Session-Token`. The CLI never places a session in a URL or query parameter.

## Routes Used by the CLI

| Operation | Method and path | Request | Success response | Error response |
| --- | --- | --- | --- | --- |
| Login | `POST /auth/login` | `email`, `password` | `session_token`, `user` | `401` invalid credentials; `403` inactive or incomplete account |
| Identity | `GET /auth/me` | session header | user `id`, `name`, `email`, `is_master`, `is_active`, `permissions` | `401` invalid or missing session |
| Projects list | `GET /projects` | session header | array of accessible projects | `401` missing session |
| Project detail | `GET /projects/{project_id}` | session header | one accessible project | `401`, `403`, `404` |
| Tasks query | `POST /tasks/query` | `project_id`, `page`, `page_size`, optional filters | `items`, `total`, `page`, `page_size`, `query_text`, `applied_order` | `401`, `403`, `400`/`422` input errors |

The current backend error body is `{ "detail": "..." }`. The CLI maps these HTTP statuses to its stable exit codes; it does not rely on localized error text for control flow.

## Compatibility Rules

- A project or task response keeps its stable identifier fields: `id`, `key` where applicable, and `project_id` for tasks.
- A task query page echoes the requested `page` and `page_size`, and its `total` counts all matching authorized tasks.
- Explicit access to a project outside the authenticated user's membership returns `403`; it is never represented as a successful empty page.
- All files in `fixtures/` use synthetic identifiers and the literal `<redacted-session-token>` placeholder. They are examples of shape only, not replayable credentials.

## Fixture Set

| Fixture | Scenario |
| --- | --- |
| `login.success.json` | successful login with a redacted session placeholder |
| `identity.success.json` | authenticated identity |
| `projects.list.success.json` | accessible project listing |
| `projects.show.success.json` | project detail for a member |
| `tasks.query.success.json` | paginated task result |
| `errors.401.json` | missing or invalid session |
| `errors.403.json` | inaccessible project |
