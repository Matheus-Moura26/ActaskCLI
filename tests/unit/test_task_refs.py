import pytest

from actask_cli.task_refs import TaskReferenceError, build_task_url, parse_task_reference

TASK_ID = "3f6a2c1e-8b4d-4e2a-9c1f-0a1b2c3d4e5f"


@pytest.mark.parametrize(
    "reference",
    [
        f"https://actask.bluefronte.com/tasks/all?task={TASK_ID}",
        f"https://actaskstage.bluefronte.com/tasks/all?task={TASK_ID}",
        f"https://actaskdev.bluefronte.com/tasks/all?task={TASK_ID}&comment=comment-1",
        f"https://actask.bluefronte.com/tasks/all?project=project-1&task={TASK_ID}&view=board",
        f"http://localhost:3000/tasks/all?task={TASK_ID}",
        f"actask.bluefronte.com/tasks/all?task={TASK_ID}",
        f"  https://actask.bluefronte.com/tasks/all?task={TASK_ID}  ",
    ],
)
def test_parse_task_reference_extracts_task_id_from_web_urls(reference: str) -> None:
    assert parse_task_reference(reference) == TASK_ID


def test_parse_task_reference_decodes_percent_encoded_task_id() -> None:
    url = "https://actask.bluefronte.com/tasks/all?task=task%2D1"

    assert parse_task_reference(url) == "task-1"


def test_parse_task_reference_uses_the_first_task_parameter() -> None:
    url = "https://actask.bluefronte.com/tasks/all?task=task-1&task=task-2"

    assert parse_task_reference(url) == "task-1"


@pytest.mark.parametrize(
    "task_value",
    ["..%2F..%2Fusers%2Fme", "a%3Fx%3D1", "a%23b", "a%2520b", "a%20b"],
)
def test_parse_task_reference_rejects_ids_that_would_change_the_api_path(
    task_value: str,
) -> None:
    with pytest.raises(TaskReferenceError, match="invalid task ID"):
        parse_task_reference(f"https://actask.bluefronte.com/tasks/all?task={task_value}")


@pytest.mark.parametrize("reference", [TASK_ID, f"  {TASK_ID} ", "MMS-152"])
def test_parse_task_reference_keeps_plain_ids_and_keys(reference: str) -> None:
    assert parse_task_reference(reference) == reference.strip()


@pytest.mark.parametrize(
    ("reference", "message"),
    [
        ("https://actask.bluefronte.com/tasks/all", "'task' parameter"),
        ("https://actask.bluefronte.com/tasks/all?task=", "'task' parameter"),
        ("https://actask.bluefronte.com/projects?task=task-1", "not an Actask task URL"),
        ("https://actask.bluefronte.com/tasksfoo?task=task-1", "not an Actask task URL"),
        ("ftp://actask.bluefronte.com/tasks/all?task=task-1", "not an Actask task URL"),
        ("actask.bluefronte.com/tasks/all", "'task' parameter"),
        ("actask.bluefronte.com/tasks/all?comment=1", "'task' parameter"),
    ],
)
def test_parse_task_reference_rejects_urls_without_a_task(reference: str, message: str) -> None:
    with pytest.raises(TaskReferenceError, match=message):
        parse_task_reference(reference)


def test_build_task_url_matches_web_app_format() -> None:
    assert build_task_url("https://actask.bluefronte.com/", TASK_ID) == (
        f"https://actask.bluefronte.com/tasks/all?task={TASK_ID}"
    )
    assert build_task_url("https://actask.example.test", "task/1") == (
        "https://actask.example.test/tasks/all?task=task%2F1"
    )
