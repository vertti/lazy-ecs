"""Tests for ServiceUI class."""

from unittest.mock import Mock, patch

import pytest

from lazy_ecs.features.service.actions import ServiceActions
from lazy_ecs.features.service.service import ServiceService
from lazy_ecs.features.service.ui import ServiceUI


@pytest.fixture
def mock_ecs_client():
    """Create a mock ECS client."""
    return Mock()


@pytest.fixture
def service_ui(mock_ecs_client):
    """Create a ServiceUI instance with mocked services."""
    service_service = ServiceService(mock_ecs_client)
    service_actions = ServiceActions(mock_ecs_client)
    return ServiceUI(service_service, service_actions)


@patch("lazy_ecs.features.service.ui.questionary.select")
def test_select_service_with_services(mock_select, service_ui):
    """Test service selection with available services."""
    service_ui.service_service.get_service_info = Mock(
        return_value=[
            {
                "name": "✅ web-api (2/2)",
                "status": "HEALTHY",
                "running_count": 2,
                "desired_count": 2,
                "pending_count": 0,
            }
        ]
    )
    mock_select.return_value.ask.return_value = "service:web-api"

    selected = service_ui.select_service("production")

    assert selected == "service:web-api"
    mock_select.assert_called_once()


def test_select_service_no_services(service_ui):
    """Test service selection with no services available."""
    service_ui.service_service.get_service_info = Mock(return_value=[])

    selected = service_ui.select_service("production")

    assert selected == "navigation:back"


@patch("lazy_ecs.features.service.ui.questionary.select")
def test_select_service_navigation_back(mock_select, service_ui):
    """Test service selection navigation back."""
    service_ui.service_service.get_service_info = Mock(
        return_value=[
            {
                "name": "✅ web-api (2/2)",
                "status": "HEALTHY",
                "running_count": 2,
                "desired_count": 2,
                "pending_count": 0,
            }
        ]
    )
    mock_select.return_value.ask.return_value = "navigation:back"

    selected = service_ui.select_service("production")

    assert selected == "navigation:back"
    mock_select.assert_called_once()


@patch("lazy_ecs.features.service.ui.questionary.select")
def test_select_service_action_with_tasks(mock_select, service_ui):
    """Test service action selection with tasks available."""
    task_info = [{"name": "task-1", "value": "task-arn-1"}]
    mock_select.return_value.ask.return_value = "task:show_details:task-arn-1"

    selected = service_ui.select_service_action("web-api", task_info)

    assert selected == "task:show_details:task-arn-1"
    mock_select.assert_called_once()


@patch("lazy_ecs.features.service.ui.questionary.confirm")
def test_handle_force_deployment_success(mock_confirm, service_ui):
    """Test successful force deployment."""
    mock_confirm.return_value.ask.return_value = True
    service_ui.service_actions.force_new_deployment = Mock(return_value=True)

    service_ui.handle_force_deployment("test-cluster", "web-api")

    service_ui.service_actions.force_new_deployment.assert_called_once_with("test-cluster", "web-api")
    mock_confirm.assert_called_once()


@patch("lazy_ecs.features.service.ui.questionary.confirm")
def test_handle_force_deployment_failure(mock_confirm, service_ui):
    """Test failed force deployment."""
    mock_confirm.return_value.ask.return_value = True
    service_ui.service_actions.force_new_deployment = Mock(return_value=False)

    service_ui.handle_force_deployment("test-cluster", "web-api")

    service_ui.service_actions.force_new_deployment.assert_called_once_with("test-cluster", "web-api")
    mock_confirm.assert_called_once()
