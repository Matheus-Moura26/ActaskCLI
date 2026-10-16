"""Task references accepted by commands and web links produced for tasks."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, quote, urlsplit

_SCHEME_PATTERN = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)


class TaskReferenceError(ValueError):
    """Raised when a task URL does not identify a task."""


def parse_task_reference(value: str) -> str:
    """Return the task ID from an Actask task URL, or the stripped value itself.

    Task URLs follow the web app format ``https://<host>/tasks/all?task=<id>``.
    The host is not checked: the backend remains the authority on whether the
    active user may read the task.
    """

    reference = value.strip()
    if not _looks_like_url(reference):
        return reference

    url = reference if _SCHEME_PATTERN.match(reference) else f"https://{reference}"
    parsed = urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.path.startswith("/tasks"):
        raise TaskReferenceError("The URL is not an Actask task URL.")
    task_ids = [item.strip() for item in parse_qs(parsed.query).get("task", [])]
    if not task_ids or not task_ids[0]:
        raise TaskReferenceError("The task URL does not contain the 'task' parameter.")
    return task_ids[0]


def build_task_url(web_url: str, task_id: str) -> str:
    """Return the web app link that opens the task, matching the web app's format."""

    return f"{web_url.rstrip('/')}/tasks/all?task={quote(task_id, safe='')}"


def _looks_like_url(reference: str) -> bool:
    if _SCHEME_PATTERN.match(reference):
        return True
    return "/tasks" in reference and "task=" in reference
