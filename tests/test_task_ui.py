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


@patch("lazy_ecs.features.task.ui.select_with_auto_pagination")
def test_select_task_multiple_tasks(mock_select, task_ui):
    """Test task selection with multiple tasks available."""
    task_info = [{"name": "task-1", "value": "task-arn-1"}, {"name": "task-2", "value": "task-arn-2"}]
    task_ui.task_service.get_task_info = Mock(return_value=task_info)
    mock_select.return_value = "task-arn-1"

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


@patch("lazy_ecs.features.task.ui.select_with_auto_pagination")
def test_select_task_feature_includes_show_task_details(mock_select, task_ui):
    """Test that task feature selection includes show task details as first option."""
    mock_select.return_value = "task_action:show_details"

    task_details = {"containers": [{"name": "web-api"}]}

    result = task_ui.select_task_feature(task_details)

    # Verify the call was made and get the choices (second positional arg)
    mock_select.assert_called_once()
    call_args = mock_select.call_args
    choices = call_args[0][1]  # Second positional argument

    # Check that "Show task details" is the first option
    assert len(choices) >= 2  # At least show_details, show_history
    assert choices[0]["name"] == "Show task details"
    assert choices[0]["value"] == "task_action:show_details"
    assert result == "task_action:show_details"


@patch("lazy_ecs.features.task.ui.select_with_auto_pagination")
def test_select_task_feature_show_history_is_second(mock_select, task_ui):
    """Test that show history is second option after show task details."""
    mock_select.return_value = "task_action:show_history"

    task_details = {"containers": [{"name": "web-api"}]}

    task_ui.select_task_feature(task_details)

    # Get the choices (second positional arg)
    call_args = mock_select.call_args
    choices = call_args[0][1]  # Second positional argument

    # Check that "Show task history" is the second option
    assert choices[1]["name"] == "Show task history and failures"
    assert choices[1]["value"] == "task_action:show_history"


@patch("lazy_ecs.features.task.ui.select_with_auto_pagination")
def test_select_task_with_many_tasks(mock_select, task_ui):
    task_info = [{"name": f"task-{i}", "value": f"task-arn-{i}"} for i in range(100)]
    task_ui.task_service.get_task_info = Mock(return_value=task_info)
    mock_select.return_value = "task-arn-50"

    selected = task_ui.select_task("test-cluster", "web-api", "desired-task-def-arn")

    assert selected == "task-arn-50"
    mock_select.assert_called_once()

    call_args = mock_select.call_args
    choices = call_args[0][1]
    assert len(choices) == 100


@patch("lazy_ecs.features.task.ui.select_with_auto_pagination")
def test_select_task_feature_with_many_containers(mock_select, task_ui):
    containers = [{"name": f"container-{i}"} for i in range(10)]
    task_details = {"containers": containers}
    mock_select.return_value = "container_action:tail_logs:container-5"

    result = task_ui.select_task_feature(task_details)

    assert result == "container_action:tail_logs:container-5"
    mock_select.assert_called_once()

    call_args = mock_select.call_args
    choices = call_args[0][1]
    assert len(choices) == 52
