"""Tests for TaskUI class."""

from unittest.mock import Mock, patch

import pytest

from lazy_ecs.features.task.task import TaskService
from lazy_ecs.features.task.ui import TaskUI


@pytest.fixture
def mock_ecs_client():
    """Create a mock ECS client."""
    return Mock()


@pytest.fixture
def task_ui(mock_ecs_client):
    """Create a TaskUI instance with mocked service."""
    task_service = TaskService(mock_ecs_client)
    return TaskUI(task_service)


@patch("lazy_ecs.features.task.ui.questionary.select")
def test_select_task_multiple_tasks(mock_select, task_ui):
    """Test task selection with multiple tasks available."""
    task_info = [{"name": "task-1", "value": "task-arn-1"}, {"name": "task-2", "value": "task-arn-2"}]
    task_ui.task_service.get_task_info = Mock(return_value=task_info)
    mock_select.return_value.ask.return_value = "task-arn-1"

    selected = task_ui.select_task("test-cluster", "web-api", "desired-task-def-arn")

    assert selected == "task-arn-1"
    mock_select.assert_called_once()


def test_select_task_auto_select_single_task(task_ui):
    """Test task selection with single task (auto-select)."""
    task_info = [{"name": "task-1", "value": "task-arn-1"}]
    task_ui.task_service.get_task_info = Mock(return_value=task_info)

    selected = task_ui.select_task("test-cluster", "web-api", "desired-task-def-arn")

    assert selected == "task-arn-1"


def test_select_task_no_tasks(task_ui):
    """Test task selection with no tasks available."""
    task_ui.task_service.get_task_info = Mock(return_value=[])

    selected = task_ui.select_task("test-cluster", "web-api", "desired-task-def-arn")

    assert selected == ""


def test_display_task_details_success(task_ui):
    """Test displaying task details successfully."""
    task_details = {
        "task_arn": "arn:aws:ecs:us-east-1:123456789012:task/test-cluster/abc123",
        "task_definition_name": "web-api",
        "task_definition_revision": "5",
        "is_desired_version": True,
        "task_status": "RUNNING",
        "containers": [
            {"name": "web-api", "image": "nginx:latest", "cpu": 256, "memory": 512, "memoryReservation": None}
        ],
        "created_at": None,
        "started_at": None,
    }

    # This test mainly ensures no exceptions are thrown
    task_ui.display_task_details(task_details)
    # If we get here without exception, the test passes


def test_display_task_details_none(task_ui):
    """Test displaying task details with None input."""
    # This test mainly ensures no exceptions are thrown
    task_ui.display_task_details(None)
    # If we get here without exception, the test passes
