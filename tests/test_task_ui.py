"""Tests for TaskUI class."""

from unittest.mock import Mock, patch

import pytest

from lazy_ecs.features.task.task import DEFAULT_STOPPED_TASK_HISTORY_LIMIT, TaskService
from lazy_ecs.features.task.ui import TaskUI


@pytest.fixture
def task_ui(mock_ecs_client):
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
            {"name": "web-api", "image": "nginx:latest", "cpu": 256, "memory": 512, "memoryReservation": None},
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
    task_action_count = sum(1 for c in choices if c["value"].startswith("task_action:"))
    container_action_count = sum(1 for c in choices if c["value"].startswith("container_action:"))
    assert len(choices) == task_action_count + container_action_count
    assert container_action_count == len(containers) * 5  # 5 actions per container


@patch("lazy_ecs.features.task.ui.select_with_auto_pagination")
def test_select_task_feature_includes_stop_task(mock_select, task_ui):
    task_details = {"containers": [{"name": "web-api"}]}
    mock_select.return_value = "task_action:stop_task"

    result = task_ui.select_task_feature(task_details)

    call_args = mock_select.call_args
    choices = call_args[0][1]

    stop_task_choices = [c for c in choices if c["value"] == "task_action:stop_task"]
    assert len(stop_task_choices) == 1
    assert stop_task_choices[0]["name"] == "Stop task"
    assert result == "task_action:stop_task"


@patch("lazy_ecs.features.task.ui.console.print")
@patch("lazy_ecs.features.task.ui.show_spinner")
@patch("lazy_ecs.features.task.ui.questionary.confirm")
def test_handle_stop_task_confirmed(mock_confirm, mock_spinner, mock_print, task_ui):
    mock_confirm.return_value.ask.return_value = True
    mock_spinner.return_value.__enter__ = Mock()
    mock_spinner.return_value.__exit__ = Mock()
    task_ui.task_service.stop_task = Mock(return_value=(True, None))

    task_ui.handle_stop_task(
        "test-cluster",
        "arn:aws:ecs:us-east-1:123456789012:task/test-cluster/abc123def456",
        "web-api",
    )

    mock_confirm.assert_called_once()
    mock_spinner.assert_called_once()
    task_ui.task_service.stop_task.assert_called_once_with(
        "test-cluster",
        "arn:aws:ecs:us-east-1:123456789012:task/test-cluster/abc123def456",
    )
    success_call = [c for c in mock_print.call_args_list if c.args and "stopped successfully" in c.args[0]]
    assert len(success_call) == 1


@patch("lazy_ecs.features.task.ui.console.print")
@patch("lazy_ecs.features.task.ui.questionary.confirm")
def test_handle_stop_task_cancelled(mock_confirm, _mock_print, task_ui):
    mock_confirm.return_value.ask.return_value = False
    task_ui.task_service.stop_task = Mock()

    task_ui.handle_stop_task("test-cluster", "arn:task:123", "web-api")

    task_ui.task_service.stop_task.assert_not_called()


@patch("lazy_ecs.features.task.ui.console.print")
@patch("lazy_ecs.features.task.ui.show_spinner")
@patch("lazy_ecs.features.task.ui.questionary.confirm")
def test_handle_stop_task_failure(mock_confirm, mock_spinner, mock_print, task_ui):
    mock_confirm.return_value.ask.return_value = True
    mock_spinner.return_value.__enter__ = Mock()
    mock_spinner.return_value.__exit__ = Mock()
    task_ui.task_service.stop_task = Mock(return_value=(False, "Access denied"))

    task_ui.handle_stop_task("test-cluster", "arn:task:abc123", "web-api")

    task_ui.task_service.stop_task.assert_called_once_with("test-cluster", "arn:task:abc123")
    error_call = [c for c in mock_print.call_args_list if c.args and "Failed to stop task: Access denied" in c.args[0]]
    assert len(error_call) == 1


def _build_task_history_entry(task_arn: str, last_status: str) -> dict:
    return {
        "task_arn": task_arn,
        "task_definition_name": "web",
        "task_definition_revision": "5",
        "last_status": last_status,
        "desired_status": last_status,
        "stop_code": None,
        "stopped_reason": None,
        "created_at": None,
        "started_at": None,
        "stopped_at": None,
        "containers": [],
    }


def test_display_task_history_shows_count_and_default_cap_notice(mocker, task_ui):
    mock_print = mocker.patch("lazy_ecs.features.task.ui.console.print")
    mock_spinner = mocker.patch("lazy_ecs.features.task.ui.show_spinner")
    mock_spinner.return_value.__enter__.return_value = None
    mock_spinner.return_value.__exit__.return_value = None

    task_ui.task_service.get_task_history = mocker.MagicMock(
        return_value=[
            _build_task_history_entry("arn:task/run-1", "RUNNING"),
            _build_task_history_entry("arn:task/stop-1", "STOPPED"),
        ],
    )
    task_ui.task_service.get_task_failure_analysis = mocker.MagicMock(return_value="ok")

    task_ui.display_task_history("production", "web")

    task_ui.task_service.get_task_history.assert_called_once_with(
        "production",
        "web",
        stopped_limit=DEFAULT_STOPPED_TASK_HISTORY_LIMIT,
    )
    printed = [str(call.args[0]) for call in mock_print.call_args_list if call.args]
    assert any("Showing 2 of 2 fetched tasks." in line for line in printed)
    assert any(
        f"⚠️ Stopped task history fetch is capped at {DEFAULT_STOPPED_TASK_HISTORY_LIMIT} tasks." in line
        for line in printed
    )


def test_display_task_history_hides_cap_notice_when_uncapped(mocker, task_ui):
    mock_print = mocker.patch("lazy_ecs.features.task.ui.console.print")
    mock_spinner = mocker.patch("lazy_ecs.features.task.ui.show_spinner")
    mock_spinner.return_value.__enter__.return_value = None
    mock_spinner.return_value.__exit__.return_value = None

    task_ui.task_service.get_task_history = mocker.MagicMock(
        return_value=[_build_task_history_entry("arn:task/run-1", "RUNNING")],
    )
    task_ui.task_service.get_task_failure_analysis = mocker.MagicMock(return_value="ok")

    task_ui.display_task_history("production", "web", stopped_limit=None)

    task_ui.task_service.get_task_history.assert_called_once_with("production", "web", stopped_limit=None)
    printed = [str(call.args[0]) for call in mock_print.call_args_list if call.args]
    assert any("Showing 1 of 1 fetched tasks." in line for line in printed)
    assert not any("⚠️ Stopped task history fetch is capped at" in line for line in printed)
