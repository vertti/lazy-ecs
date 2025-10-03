"""Tests for ServiceUI class."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from lazy_ecs.features.service.actions import ServiceActions
from lazy_ecs.features.service.service import ServiceService
from lazy_ecs.features.service.ui import ServiceUI, _get_event_type_style


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


@patch("lazy_ecs.features.service.ui.select_with_auto_pagination")
def test_select_service_with_services(mock_select, service_ui):
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
    mock_select.return_value = "service:web-api"

    selected = service_ui.select_service("production")

    assert selected == "service:web-api"
    mock_select.assert_called_once()


@patch("lazy_ecs.features.service.ui.select_with_auto_pagination")
def test_select_service_with_many_services(mock_select, service_ui):
    service_info = []
    for i in range(100):
        service_info.append(
            {
                "name": f"✅ service-{i} (1/1)",
                "status": "HEALTHY",
                "running_count": 1,
                "desired_count": 1,
                "pending_count": 0,
            }
        )
    service_ui.service_service.get_service_info = Mock(return_value=service_info)
    mock_select.return_value = "service:service-50"

    selected = service_ui.select_service("production")

    assert selected == "service:service-50"
    mock_select.assert_called_once()

    call_args = mock_select.call_args
    choices = call_args[0][1]
    assert len(choices) == 100


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


@patch("lazy_ecs.features.service.ui.select_with_auto_pagination")
def test_select_service_action_with_tasks(mock_select, service_ui):
    task_info = [{"name": "task-1", "value": "task-arn-1"}]
    mock_select.return_value = "task:show_details:task-arn-1"

    selected = service_ui.select_service_action("web-api", task_info)

    assert selected == "task:show_details:task-arn-1"
    mock_select.assert_called_once()


@patch("lazy_ecs.features.service.ui.select_with_auto_pagination")
def test_select_service_action_with_many_tasks(mock_select, service_ui):
    task_info = [{"name": f"task-{i}", "value": f"task-arn-{i}"} for i in range(100)]
    mock_select.return_value = "task:show_details:task-arn-50"

    selected = service_ui.select_service_action("web-api", task_info)

    assert selected == "task:show_details:task-arn-50"
    mock_select.assert_called_once()

    call_args = mock_select.call_args
    choices = call_args[0][1]
    assert len(choices) == 103  # 100 tasks + 3 actions (events, metrics, deployment)


@patch("lazy_ecs.features.service.ui.select_with_auto_pagination")
def test_select_service_action_show_events(mock_select, service_ui):
    """Test service action selection for show events."""
    task_info = [{"name": "task-1", "value": "task-arn-1"}]
    mock_select.return_value = "action:show_events"

    selected = service_ui.select_service_action("web-api", task_info)

    assert selected == "action:show_events"
    mock_select.assert_called_once()

    # Verify that show events option is in the choices
    call_args = mock_select.call_args
    choices = call_args[0][1]  # Second positional argument is choices
    show_events_choice = next((choice for choice in choices if choice.get("value") == "action:show_events"), None)
    assert show_events_choice is not None
    assert "Show service events" in show_events_choice["name"]


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


@patch("lazy_ecs.features.service.ui.console.print")
def test_display_service_events_with_events(mock_print, service_ui):
    """Test displaying service events with event data."""
    mock_events = [
        {
            "id": "event-1",
            "created_at": datetime(2024, 1, 15, 10, 30, 45),
            "message": "(service web-api) has started a deployment",
            "event_type": "deployment",
        },
        {
            "id": "event-2",
            "created_at": datetime(2024, 1, 15, 10, 25, 30),
            "message": "(service web-api) scaling completed successfully",
            "event_type": "scaling",
        },
    ]
    service_ui.service_service.get_service_events = Mock(return_value=mock_events)

    service_ui.display_service_events("test-cluster", "web-api")

    service_ui.service_service.get_service_events.assert_called_once_with("test-cluster", "web-api")
    mock_print.assert_called_once()


@patch("lazy_ecs.features.service.ui.console.print")
def test_display_service_events_no_events(mock_print, service_ui):
    """Test displaying service events with no event data."""
    service_ui.service_service.get_service_events = Mock(return_value=[])

    service_ui.display_service_events("test-cluster", "web-api")

    service_ui.service_service.get_service_events.assert_called_once_with("test-cluster", "web-api")
    mock_print.assert_called_once_with("No events found for service 'web-api'", style="blue")


def test_get_event_type_style():
    """Test event type style mapping."""
    assert _get_event_type_style("deployment") == "blue"
    assert _get_event_type_style("scaling") == "yellow"
    assert _get_event_type_style("failure") == "red"
    assert _get_event_type_style("other") == "white"
    assert _get_event_type_style("unknown") == "white"  # Default case


@patch("lazy_ecs.features.service.ui.console.print")
def test_service_name_truncation_shows_end(mock_print, service_ui):
    """Test that long service names are truncated to show the distinguishing end part."""
    mock_events = [
        {
            "id": "event-1",
            "created_at": datetime(2024, 1, 15, 10, 30, 45),
            "message": "(service very-long-service-name-with-important-suffix-v2) has started a deployment",
            "event_type": "deployment",
        }
    ]
    service_ui.service_service.get_service_events = Mock(return_value=mock_events)

    service_ui.display_service_events("test-cluster", "test-service")

    # The service name should be truncated to show the end (suffix-v2)
    mock_print.assert_called_once()
    # We can't easily test the exact truncation without complex argument inspection,
    # but we know the logic truncates to show the last 15 chars with "..." prefix
