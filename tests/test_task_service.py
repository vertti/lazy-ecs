"""Tests for task service."""

from unittest.mock import Mock

from lazy_ecs.features.task.task import TaskService


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
