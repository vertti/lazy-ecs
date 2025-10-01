"""Tests for ECSNavigator orchestration layer."""

from unittest.mock import Mock, patch

import pytest

from lazy_ecs.ui import ECSNavigator


@pytest.fixture
def mock_ecs_service() -> Mock:
    """Create a mock ECS service."""
    return Mock()


def test_navigator_initialization(mock_ecs_service) -> None:
    """Test that ECSNavigator properly initializes all UI components."""
    navigator = ECSNavigator(mock_ecs_service)

    assert navigator._cluster_ui is not None
    assert navigator._service_ui is not None
    assert navigator._task_ui is not None
    assert navigator._container_ui is not None


def test_select_cluster_delegates_to_cluster_ui(mock_ecs_service) -> None:
    """Test that select_cluster delegates to ClusterUI."""
    navigator = ECSNavigator(mock_ecs_service)
    navigator._cluster_ui.select_cluster = Mock(return_value="production")

    result = navigator.select_cluster()

    assert result == "production"
    navigator._cluster_ui.select_cluster.assert_called_once()


def test_select_service_delegates_to_service_ui(mock_ecs_service) -> None:
    """Test that select_service delegates to ServiceUI."""
    navigator = ECSNavigator(mock_ecs_service)
    navigator._service_ui.select_service = Mock(return_value="service:web-api")

    result = navigator.select_service("production")

    assert result == "service:web-api"
    navigator._service_ui.select_service.assert_called_once_with("production")


def test_select_service_action_integration(mock_ecs_service) -> None:
    """Test that select_service_action integrates ECSService and ServiceUI."""
    mock_ecs_service.get_task_info.return_value = [{"name": "task-1", "value": "task-arn-1"}]

    navigator = ECSNavigator(mock_ecs_service)
    navigator._service_ui.select_service_action = Mock(return_value="task:show_details:task-arn-1")

    result = navigator.select_service_action("production", "web-api")

    assert result == "task:show_details:task-arn-1"
    mock_ecs_service.get_task_info.assert_called_once_with("production", "web-api")
    navigator._service_ui.select_service_action.assert_called_once_with(
        "web-api", [{"name": "task-1", "value": "task-arn-1"}]
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
    """Test that handle_force_deployment delegates to ServiceUI."""
    navigator = ECSNavigator(mock_ecs_service)
    navigator._service_ui.handle_force_deployment = Mock()

    navigator.handle_force_deployment("cluster", "service")

    navigator._service_ui.handle_force_deployment.assert_called_once_with("cluster", "service")


def test_build_task_feature_choices() -> None:
    """Test the build_task_feature_choices utility function."""
    from lazy_ecs.ui import _build_task_feature_choices

    containers = [{"name": "web"}, {"name": "sidecar"}]
    choices = _build_task_feature_choices(containers)

    # Verify structure
    choice_names = [choice["name"] for choice in choices]
    choice_values = [choice["value"] for choice in choices]

    # Check container actions are present
    assert "Show logs (tail) for container: web" in choice_names
    assert "Show environment variables for container: web" in choice_names
    assert "Show secrets for container: web" in choice_names
    assert "Show port mappings for container: web" in choice_names
    assert "Show volume mounts for container: web" in choice_names

    assert "Show logs (tail) for container: sidecar" in choice_names
    assert "Show environment variables for container: sidecar" in choice_names
    assert "Show secrets for container: sidecar" in choice_names
    assert "Show port mappings for container: sidecar" in choice_names
    assert "Show volume mounts for container: sidecar" in choice_names

    # Check navigation
    assert "⬅️ Back to service selection" in choice_names
    assert "❌ Exit" in choice_names

    # Check values
    assert "container_action:tail_logs:web" in choice_values
    assert "container_action:show_env:web" in choice_values
    assert "navigation:back" in choice_values
    assert "navigation:exit" in choice_values

    # Total: 5 actions x 2 containers + 2 navigation = 12
    assert len(choices) == 12
