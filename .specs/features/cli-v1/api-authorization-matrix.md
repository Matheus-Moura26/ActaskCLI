# Actask CLI v1 API Authorization Matrix

**Inventory date:** 2026-07-10
**Backend:** `ActaskBack` branch `dev`
**Scope:** routes needed by CLI-001 through CLI-016.

## Shared Rules

- Authenticated routes use `X-Session-Token`; no credential belongs in a URL or query string.
- `app.middleware.auth.get_current_user` returns `401` for an absent, expired, invalid, or inactive session.
- `is_master` has unrestricted project access. Other users need a `ProjectUser` association unless a route states a global permission requirement.
- The CLI must preserve backend `401` and `403`; it must not turn either into an empty successful result.

## Route Matrix

| CLI requirement | CLI operation | Backend route | Authentication | Server-side authorization and scope | Expected responses | Evidence / status |
| --- | --- | --- | --- | --- | --- | --- |
| CLI-001, CLI-002 | login | `POST /auth/login` | No | Validates email/password and active/password-set state | `200`, `401` bad credentials, `403` inactive or password not set | `app/routes/auth.py:22` |
| CLI-003 | logout | `POST /auth/logout` | Required | Resolves session before deleting the user's sessions | `200`, `401` invalid session | `app/routes/auth.py:35` |
| CLI-004, CLI-005 | whoami | `GET /auth/me` | Required | Returns only the authenticated user | `200`, `401` invalid session | `app/routes/auth.py:44`; `app/middleware/auth.py:27` |
| CLI-006, CLI-009 | authenticated transport | all protected routes | Required | `get_current_user` is the server authority; `require_permission` returns `403` for missing global permission | `401` unauthenticated, `403` forbidden | `app/middleware/auth.py:27`, `app/middleware/auth.py:46` |
| CLI-011 | projects list | `GET /projects` | Required | Non-master query is restricted to `ProjectUser.user_id`; master sees all | `200`, `401` | `app/routes/projects.py:105` |
| CLI-012 | projects show | `GET /projects/{project_id}` | Required | Must require membership or master before returning the project | `200`, `401`, `403`, `404` | **GAP-01:** route does not exist |
| CLI-013, CLI-017 | tasks list with filters and pagination | `POST /tasks/query` | Required | `TaskQueryAccessScope` filters database query to member projects; with an explicit inaccessible `project_id` it must return `403` | `200` paginated `{items,total,page,page_size,...}`, `401`, `403` | `app/routes/tasks.py:1472`; `app/services/task_query.py:857`; **GAP-02:** inaccessible explicit project currently becomes empty `200` |
| CLI-013 (legacy compatibility) | tasks list | `GET /tasks?project_id=...` | Required | Filters query to member projects, but returns empty `200` for an explicit inaccessible project | `200`, `401` | `app/routes/tasks.py:1218`; not selected by the CLI because it cannot satisfy the required forbidden response |
| CLI-014 | tasks show | `GET /tasks/{task_id}` | Required | Loads the task then requires master or `ProjectUser` membership | `200`, `401`, `403`, `404` | `app/routes/tasks.py:364`, `app/routes/tasks.py:1606` |
| CLI-015 | tasks create | `POST /tasks` | Required | Requires master or `ProjectUser` membership for `project_id`; validates project and task data server-side | `200`, `401`, `403`, `404`, `422` | `app/routes/tasks.py:1523` |
| CLI-015 | tasks update | `PUT /tasks/{task_id}` | Required | Requires access to existing task project; moving project/column additionally requires `moveTasks` unless master, and target project access is checked | `200`, `401`, `403`, `404`, `422` | `app/routes/tasks.py:1657` |
| CLI-016 | destructive actions | None in v1 | N/A | No task deletion route is selected for v1 | N/A | Explicitly out of CLI v1 surface |

## Gaps Routed to T02

1. **GAP-01:** add `GET /projects/{project_id}` returning `ProjectOut`, protected by session authentication and project membership. A non-member must receive `403`; an authenticated request for a missing project must receive `404`.
2. **GAP-02:** change `POST /tasks/query` so a non-master explicitly querying a project without membership receives `403`, rather than a successful empty page. This is required by CLI-007, CLI-009, CLI-010, and AC-02.

## Non-blocking Observations

- `GET /projects/{project_id}/columns` and `GET /projects/{project_id}/users` lack a membership check. They are not part of the CLI v1 route set, so they remain out of scope for this phase; the CLI must not call them.
- `POST /auth/logout` invalidates every session for the authenticated user, not just the supplied session. This satisfies CLI-003 but is a broader existing behavior; no contract change is made in this phase.
