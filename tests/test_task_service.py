"""Tests for task service."""

from unittest.mock import Mock, call

from lazy_ecs.features.task.task import (
    DEFAULT_STOPPED_TASK_HISTORY_LIMIT,
    TaskService,
    _create_task_info,
    _get_brief_exit_reason,
    _get_brief_failure_reason,
    _get_brief_stop_reason,
)


def test_get_task_details_returns_none_when_no_tasks():
    mock_ecs_client = Mock()
    mock_ecs_client.describe_tasks.return_value = {"tasks": []}
    task_service = TaskService(mock_ecs_client)

    result = task_service.get_task_details("cluster", "task-arn", None)

    assert result is None


def test_get_task_and_definition_returns_none_when_no_tasks():
    mock_ecs_client = Mock()
    mock_ecs_client.describe_tasks.return_value = {"tasks": []}
    task_service = TaskService(mock_ecs_client)

    result = task_service.get_task_and_definition("cluster", "task-arn")

    assert result is None


def test_get_task_and_definition_returns_none_when_no_task_definition():
    mock_ecs_client = Mock()
    mock_ecs_client.describe_tasks.return_value = {
        "tasks": [{"taskArn": "arn:task", "taskDefinitionArn": "arn:task-def:1"}]
    }
    mock_ecs_client.describe_task_definition.return_value = {}
    task_service = TaskService(mock_ecs_client)

    result = task_service.get_task_and_definition("cluster", "task-arn")

    assert result is None


def test_stop_task_success():
    mock_ecs_client = Mock()
    mock_ecs_client.stop_task.return_value = {"task": {"taskArn": "arn:task"}}
    task_service = TaskService(mock_ecs_client)

    success, error = task_service.stop_task("test-cluster", "arn:task:123")

    assert success is True
    assert error is None
    mock_ecs_client.stop_task.assert_called_once_with(
        cluster="test-cluster",
        task="arn:task:123",
        reason="Stopped via lazy-ecs",
    )


def test_stop_task_with_custom_reason():
    mock_ecs_client = Mock()
    mock_ecs_client.stop_task.return_value = {"task": {"taskArn": "arn:task"}}
    task_service = TaskService(mock_ecs_client)

    success, error = task_service.stop_task("test-cluster", "arn:task:123", reason="Manual restart")

    assert success is True
    assert error is None
    mock_ecs_client.stop_task.assert_called_once_with(
        cluster="test-cluster",
        task="arn:task:123",
        reason="Manual restart",
    )


def test_stop_task_client_error():
    from botocore.exceptions import ClientError

    mock_ecs_client = Mock()
    mock_ecs_client.stop_task.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
        "StopTask",
    )
    task_service = TaskService(mock_ecs_client)

    success, error = task_service.stop_task("test-cluster", "arn:task:123")

    assert success is False
    assert error == "Access denied"
    mock_ecs_client.stop_task.assert_called_once_with(
        cluster="test-cluster",
        task="arn:task:123",
        reason="Stopped via lazy-ecs",
    )


# Brief failure reason tests


def test_get_brief_exit_reason_sigkill():
    assert _get_brief_exit_reason(137) == "SIGKILL"


def test_get_brief_exit_reason_segfault():
    assert _get_brief_exit_reason(139) == "segfault"


def test_get_brief_exit_reason_sigterm():
    assert _get_brief_exit_reason(143) == "SIGTERM"


def test_get_brief_exit_reason_app_error():
    assert _get_brief_exit_reason(1) == "app error"


def test_get_brief_exit_reason_unknown():
    assert _get_brief_exit_reason(42) == "exit 42"


def test_get_brief_stop_reason_failed_to_start():
    assert _get_brief_stop_reason("TaskFailedToStart") == "failed to start"


def test_get_brief_stop_reason_scheduler():
    assert _get_brief_stop_reason("ServiceSchedulerInitiated") == "scheduler stopped"


def test_get_brief_stop_reason_spot():
    assert _get_brief_stop_reason("SpotInterruption") == "spot interrupted"


def test_get_brief_stop_reason_user():
    assert _get_brief_stop_reason("UserInitiated") == "user stopped"


def test_get_brief_stop_reason_unknown():
    assert _get_brief_stop_reason("SomeOtherCode") == "someothercode"


def test_get_brief_stop_reason_none():
    assert _get_brief_stop_reason(None) is None


def test_get_brief_failure_reason_running_task():
    task = {"lastStatus": "RUNNING", "containers": []}
    assert _get_brief_failure_reason(task) is None


def test_get_brief_failure_reason_sigkill():
    task = {"lastStatus": "STOPPED", "containers": [{"exitCode": 137}]}
    assert _get_brief_failure_reason(task) == "SIGKILL"


def test_get_brief_failure_reason_app_error():
    task = {"lastStatus": "STOPPED", "containers": [{"exitCode": 1}]}
    assert _get_brief_failure_reason(task) == "app error"


def test_get_brief_failure_reason_failed_to_start():
    task = {"lastStatus": "STOPPED", "containers": [], "stopCode": "TaskFailedToStart"}
    assert _get_brief_failure_reason(task) == "failed to start"


def test_get_brief_failure_reason_container_success():
    task = {"lastStatus": "STOPPED", "containers": [{"exitCode": 0}], "stopCode": "UserInitiated"}
    assert _get_brief_failure_reason(task) == "user stopped"


def test_create_task_info_includes_failure_reason():
    task = {
        "taskArn": "arn:aws:ecs:us-east-1:123:task/cluster/abc123def456",
        "taskDefinitionArn": "arn:aws:ecs:us-east-1:123:task-definition/web:5",
        "lastStatus": "STOPPED",
        "containers": [{"exitCode": 137, "image": "nginx:latest"}],
    }
    info = _create_task_info(task, None)
    assert "SIGKILL" in info["name"]
    assert info["failure_reason"] == "SIGKILL"


def test_create_task_info_no_failure_for_running():
    task = {
        "taskArn": "arn:aws:ecs:us-east-1:123:task/cluster/abc123def456",
        "taskDefinitionArn": "arn:aws:ecs:us-east-1:123:task-definition/web:5",
        "lastStatus": "RUNNING",
        "containers": [{"image": "nginx:latest"}],
    }
    info = _create_task_info(task, None)
    assert info["failure_reason"] is None
    assert "OOM" not in info["name"]


def _build_task_history_task(task_arn: str, last_status: str) -> dict:
    return {
        "taskArn": task_arn,
        "taskDefinitionArn": "arn:aws:ecs:us-east-1:123:task-definition/web:5",
        "lastStatus": last_status,
        "desiredStatus": last_status,
        "containers": [{"name": "web", "lastStatus": last_status}],
    }


def test_get_task_history_caps_stopped_tasks_by_default_limit():
    mock_ecs_client = Mock()
    mock_paginator = Mock()
    mock_ecs_client.get_paginator.return_value = mock_paginator
    mock_paginator.paginate.side_effect = [
        iter([{"taskArns": ["run-1", "run-2"]}]),
        iter(
            [
                {"taskArns": [f"stop-{i}" for i in range(1, 26)]},
                {"taskArns": [f"stop-{i}" for i in range(26, 60)]},
            ],
        ),
    ]

    def describe_tasks_side_effect(*, cluster: str, tasks: list[str]) -> dict:
        assert cluster == "production"
        return {
            "tasks": [
                _build_task_history_task(arn, "RUNNING" if arn.startswith("run-") else "STOPPED") for arn in tasks
            ],
        }

    mock_ecs_client.describe_tasks.side_effect = describe_tasks_side_effect
    task_service = TaskService(mock_ecs_client)

    history = task_service.get_task_history("production", "web")

    assert len(history) == 2 + DEFAULT_STOPPED_TASK_HISTORY_LIMIT
    assert sum(1 for task in history if task["last_status"] == "STOPPED") == DEFAULT_STOPPED_TASK_HISTORY_LIMIT
    mock_paginator.paginate.assert_has_calls(
        [
            call(cluster="production", desiredStatus="RUNNING", serviceName="web"),
            call(cluster="production", desiredStatus="STOPPED", serviceName="web"),
        ],
    )


def test_get_task_history_allows_uncapped_stopped_task_fetch():
    mock_ecs_client = Mock()
    mock_paginator = Mock()
    mock_ecs_client.get_paginator.return_value = mock_paginator
    mock_paginator.paginate.side_effect = [
        iter([{"taskArns": ["run-1"]}]),
        iter(
            [
                {"taskArns": ["stop-1", "stop-2"]},
                {"taskArns": ["stop-3"]},
            ],
        ),
    ]

    def describe_tasks_side_effect(*, cluster: str, tasks: list[str]) -> dict:
        assert cluster == "production"
        return {
            "tasks": [
                _build_task_history_task(arn, "RUNNING" if arn.startswith("run-") else "STOPPED") for arn in tasks
            ],
        }

    mock_ecs_client.describe_tasks.side_effect = describe_tasks_side_effect
    task_service = TaskService(mock_ecs_client)

    history = task_service.get_task_history("production", "web", stopped_limit=None)

    assert len(history) == 4
    assert sum(1 for task in history if task["last_status"] == "STOPPED") == 3
