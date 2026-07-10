# Agent Instructions

Implement this repository from the approved documents in `.specs/features/cli-v1/`.

Before changing code:

1. Read `.specs/STATE.md`.
2. Read the v1 `spec.md`, `design.md` and `tasks.md` completely.
3. Follow `docs/AI_ORCHESTRATION.md`.
4. Confirm that the next task has all dependencies completed.

Security invariants:

- Never log, print, commit or pass credentials in command-line arguments.
- Never treat a CLI-side permission check as authorization.
- Preserve backend `401` and `403` responses and present actionable, non-sensitive errors.
- Scope credentials to the current operating-system user and Actask server profile.
- Require explicit confirmation for destructive actions unless `--yes` is provided.

Execution invariants:

- Implement one task at a time.
- Add tests in the same task as the behavior they verify.
- Run the task gate before committing.
- Create one atomic commit per task.
- Record decisions and handoff state in `.specs/STATE.md`.
- After the final task, use an independent verifier against every acceptance criterion.
