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
