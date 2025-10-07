"""Tests for ECSNavigator orchestration layer."""

from unittest.mock import Mock, patch

import pytest

from lazy_ecs.ui import ECSNavigator


@pytest.fixture
def mock_ecs_service() -> Mock:
    return Mock()


def test_navigator_initialization(mock_ecs_service) -> None:
    navigator = ECSNavigator(mock_ecs_service)

    assert navigator._cluster_ui is not None
    assert navigator._service_ui is not None
    assert navigator._task_ui is not None
    assert navigator._container_ui is not None


def test_select_cluster_delegates_to_cluster_ui(mock_ecs_service) -> None:
    navigator = ECSNavigator(mock_ecs_service)
    navigator._cluster_ui.select_cluster = Mock(return_value="production")

    result = navigator.select_cluster()

    assert result == "production"
    navigator._cluster_ui.select_cluster.assert_called_once()


def test_select_service_delegates_to_service_ui(mock_ecs_service) -> None:
    navigator = ECSNavigator(mock_ecs_service)
    navigator._service_ui.select_service = Mock(return_value="service:web-api")

    result = navigator.select_service("production")

    assert result == "service:web-api"
    navigator._service_ui.select_service.assert_called_once_with("production")


def test_select_service_action_integration(mock_ecs_service) -> None:
    mock_ecs_service.get_task_info.return_value = [{"name": "task-1", "value": "task-arn-1"}]

    navigator = ECSNavigator(mock_ecs_service)
    navigator._service_ui.select_service_action = Mock(return_value="task:show_details:task-arn-1")

    result = navigator.select_service_action("production", "web-api")

    assert result == "task:show_details:task-arn-1"
    mock_ecs_service.get_task_info.assert_called_once_with("production", "web-api")
    navigator._service_ui.select_service_action.assert_called_once_with(
        "web-api",
        [{"name": "task-1", "value": "task-arn-1"}],
    )


@patch("lazy_ecs.core.base.select_with_navigation")
def test_select_task_integration(mock_select, mock_ecs_service) -> None:
    """Test that select_task integrates with ECSService properly."""
    mock_ecs_service.get_task_info.return_value = [
        {"name": "task-1", "value": "task-arn-1"},
        {"name": "task-2", "value": "task-arn-2"},
    ]
    mock_select.return_value = "task-arn-1"

    navigator = ECSNavigator(mock_ecs_service)
    result = navigator.select_task("production", "web-api")

    assert result == "task-arn-1"
    mock_ecs_service.get_task_info.assert_called_once_with("production", "web-api")


def test_select_task_no_tasks(mock_ecs_service) -> None:
    """Test select_task with no tasks available."""
    mock_ecs_service.get_task_info.return_value = []

    navigator = ECSNavigator(mock_ecs_service)
    result = navigator.select_task("production", "web-api")

    assert result == ""


def test_display_task_details_delegates_to_task_ui(mock_ecs_service) -> None:
    """Test that display_task_details delegates to TaskUI."""
    from lazy_ecs.core.types import TaskDetails

    navigator = ECSNavigator(mock_ecs_service)
    navigator._task_ui.display_task_details = Mock()

    task_details: TaskDetails = {
        "task_arn": "task-123",
        "task_definition_name": "web-task",
        "task_definition_revision": "1",
        "is_desired_version": True,
        "task_status": "RUNNING",
        "containers": [],
        "created_at": None,
        "started_at": None,
    }
    navigator.display_task_details(task_details)

    navigator._task_ui.display_task_details.assert_called_once_with(task_details)


@patch("lazy_ecs.features.task.ui.select_with_auto_pagination")
def test_select_task_feature_with_containers(mock_select, mock_ecs_service) -> None:
    """Test task feature selection with containers."""
    from lazy_ecs.core.types import TaskDetails

    mock_select.return_value = "container_action:tail_logs:web"

    navigator = ECSNavigator(mock_ecs_service)
    task_details: TaskDetails = {
        "task_arn": "task-123",
        "task_definition_name": "web-task",
        "task_definition_revision": "1",
        "is_desired_version": True,
        "task_status": "RUNNING",
        "containers": [{"name": "web"}, {"name": "sidecar"}],
        "created_at": None,
        "started_at": None,
    }

    selected = navigator.select_task_feature(task_details)

    assert selected == "container_action:tail_logs:web"
    mock_select.assert_called_once()


def test_select_task_feature_no_containers(mock_ecs_service) -> None:
    """Test task feature selection with no containers."""
    navigator = ECSNavigator(mock_ecs_service)

    selected = navigator.select_task_feature(None)

    assert selected is None


def test_container_methods_delegate_to_container_ui(mock_ecs_service) -> None:
    """Test that all container methods delegate to ContainerUI."""
    navigator = ECSNavigator(mock_ecs_service)

    # Mock all ContainerUI methods
    navigator._container_ui.show_logs_live_tail = Mock()
    navigator._container_ui.show_container_environment_variables = Mock()
    navigator._container_ui.show_container_secrets = Mock()
    navigator._container_ui.show_container_port_mappings = Mock()
    navigator._container_ui.show_container_volume_mounts = Mock()

    # Test delegation
    navigator.show_container_logs_live_tail("cluster", "task", "container")
    navigator.show_container_environment_variables("cluster", "task", "container")
    navigator.show_container_secrets("cluster", "task", "container")
    navigator.show_container_port_mappings("cluster", "task", "container")
    navigator.show_container_volume_mounts("cluster", "task", "container")

    # Verify delegation
    navigator._container_ui.show_logs_live_tail.assert_called_once_with("cluster", "task", "container")
    navigator._container_ui.show_container_environment_variables.assert_called_once_with("cluster", "task", "container")
    navigator._container_ui.show_container_secrets.assert_called_once_with("cluster", "task", "container")
    navigator._container_ui.show_container_port_mappings.assert_called_once_with("cluster", "task", "container")
    navigator._container_ui.show_container_volume_mounts.assert_called_once_with("cluster", "task", "container")


def test_handle_force_deployment_delegates_to_service_ui(mock_ecs_service) -> None:
    navigator = ECSNavigator(mock_ecs_service)
    navigator._service_ui.handle_force_deployment = Mock()

    navigator.handle_force_deployment("cluster", "service")

    navigator._service_ui.handle_force_deployment.assert_called_once_with("cluster", "service")


def test_show_service_events_delegates_to_service_ui(mock_ecs_service):
    navigator = ECSNavigator(mock_ecs_service)
    navigator._service_ui.display_service_events = Mock()

    navigator.show_service_events("cluster", "service")

    navigator._service_ui.display_service_events.assert_called_once_with("cluster", "service")


@patch("lazy_ecs.ui.console")
def test_show_service_metrics_with_data(_mock_console, mock_ecs_service):
    mock_ecs_service.get_service_metrics.return_value = {"cpu": 50.0, "memory": 60.0}
    navigator = ECSNavigator(mock_ecs_service)
    navigator._service_ui.display_service_metrics = Mock()

    navigator.show_service_metrics("cluster", "service")

    navigator._service_ui.display_service_metrics.assert_called_once_with("service", {"cpu": 50.0, "memory": 60.0})


@patch("lazy_ecs.ui.console")
def test_show_service_metrics_no_data(mock_console, mock_ecs_service):
    mock_ecs_service.get_service_metrics.return_value = None
    navigator = ECSNavigator(mock_ecs_service)

    navigator.show_service_metrics("cluster", "service")

    mock_console.print.assert_any_call("\n⚠️ No metrics available for service 'service'", style="yellow")


def test_show_task_history_delegates_to_task_ui(mock_ecs_service):
    navigator = ECSNavigator(mock_ecs_service)
    navigator._task_ui.display_task_history = Mock()

    navigator.show_task_history("cluster", "service")

    navigator._task_ui.display_task_history.assert_called_once_with("cluster", "service")


def test_show_task_definition_comparison_with_details(mock_ecs_service):
    navigator = ECSNavigator(mock_ecs_service)
    navigator._task_ui.show_task_definition_comparison = Mock()
    task_details = {"taskArn": "arn:task"}

    navigator.show_task_definition_comparison(task_details)  # type: ignore[arg-type]

    navigator._task_ui.show_task_definition_comparison.assert_called_once_with(task_details)


def test_show_task_definition_comparison_without_details(mock_ecs_service):
    navigator = ECSNavigator(mock_ecs_service)
    navigator._task_ui.show_task_definition_comparison = Mock()

    navigator.show_task_definition_comparison(None)

    navigator._task_ui.show_task_definition_comparison.assert_not_called()


def test_open_service_in_console(mock_ecs_service):
    with patch("webbrowser.open") as mock_webbrowser:
        mock_ecs_service.get_region.return_value = "us-east-1"
        navigator = ECSNavigator(mock_ecs_service)

        navigator.open_service_in_console("production", "web-api")

        mock_webbrowser.assert_called_once()
        url_arg = mock_webbrowser.call_args[0][0]
        assert "us-east-1" in url_arg
        assert "production" in url_arg
        assert "web-api" in url_arg


def test_open_task_in_console(mock_ecs_service):
    with patch("webbrowser.open") as mock_webbrowser:
        mock_ecs_service.get_region.return_value = "us-west-2"
        navigator = ECSNavigator(mock_ecs_service)

        navigator.open_task_in_console("staging", "task-arn-123")

        mock_webbrowser.assert_called_once()
        url_arg = mock_webbrowser.call_args[0][0]
        assert "us-west-2" in url_arg
        assert "staging" in url_arg
        assert "task-arn-123" in url_arg
