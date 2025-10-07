"""Tests for core application logic."""

from unittest.mock import Mock, patch

from lazy_ecs.core.app import (
    dispatch_container_action,
    dispatch_service_action,
    dispatch_task_action,
    get_container_action_handlers,
    get_service_action_handlers,
    get_task_action_handlers,
    handle_task_features,
    handle_task_selection,
    navigate_services,
)


def test_get_container_action_handlers_returns_all_actions():
    handlers = get_container_action_handlers()

    assert "tail_logs" in handlers
    assert "show_env" in handlers
    assert "show_secrets" in handlers
    assert "show_ports" in handlers
    assert "show_volumes" in handlers
    assert len(handlers) == 5


def test_get_task_action_handlers_returns_all_actions():
    handlers = get_task_action_handlers()

    assert "show_history" in handlers
    assert "show_details" in handlers
    assert "compare_definitions" in handlers
    assert "open_console" in handlers
    assert len(handlers) == 4


def test_get_service_action_handlers_returns_all_actions():
    handlers = get_service_action_handlers()

    assert "force_deployment" in handlers
    assert "show_events" in handlers
    assert "show_metrics" in handlers
    assert "open_console" in handlers
    assert len(handlers) == 4


def test_dispatch_container_action_calls_handler_for_valid_action():
    mock_navigator = Mock()

    result = dispatch_container_action(mock_navigator, "cluster", "task-arn", "container", "show_env")

    assert result is True
    mock_navigator.show_container_environment_variables.assert_called_once_with("cluster", "task-arn", "container")


def test_dispatch_container_action_returns_false_for_invalid_action():
    mock_navigator = Mock()

    result = dispatch_container_action(mock_navigator, "cluster", "task-arn", "container", "invalid_action")

    assert result is False


def test_dispatch_task_action_calls_handler_for_valid_action():
    mock_navigator = Mock()

    result = dispatch_task_action(mock_navigator, "cluster", "service", "task-arn", None, "show_history")

    assert result is True
    mock_navigator.show_task_history.assert_called_once_with("cluster", "service")


def test_dispatch_task_action_returns_false_for_invalid_action():
    mock_navigator = Mock()

    result = dispatch_task_action(mock_navigator, "cluster", "service", "task-arn", None, "invalid_action")

    assert result is False


def test_dispatch_service_action_calls_handler_for_valid_action():
    mock_navigator = Mock()

    dispatch_service_action(mock_navigator, "cluster", "service", "show_events")

    mock_navigator.show_service_events.assert_called_once_with("cluster", "service")


def test_dispatch_service_action_ignores_invalid_action():
    mock_navigator = Mock()

    dispatch_service_action(mock_navigator, "cluster", "service", "invalid_action")

    assert not mock_navigator.method_calls


def test_navigate_services_returns_true_on_back():
    mock_navigator = Mock()
    mock_navigator.select_service.return_value = "navigation:back"
    mock_ecs_service = Mock()

    result = navigate_services(mock_navigator, mock_ecs_service, "cluster")

    assert result is True


def test_navigate_services_returns_false_on_exit():
    mock_navigator = Mock()
    mock_navigator.select_service.return_value = "navigation:exit"
    mock_ecs_service = Mock()

    result = navigate_services(mock_navigator, mock_ecs_service, "cluster")

    assert result is False


def test_navigate_services_returns_true_on_non_service_selection():
    mock_navigator = Mock()
    mock_navigator.select_service.return_value = "unknown:value"
    mock_ecs_service = Mock()

    result = navigate_services(mock_navigator, mock_ecs_service, "cluster")

    assert result is True


@patch("lazy_ecs.core.app.console")
def test_navigate_services_handles_service_action_back(_mock_console):
    mock_navigator = Mock()
    mock_navigator.select_service.return_value = "service:web-api"
    mock_navigator.select_service_action.return_value = "navigation:back"
    mock_ecs_service = Mock()

    result = navigate_services(mock_navigator, mock_ecs_service, "cluster")

    assert result is True


@patch("lazy_ecs.core.app.console")
def test_navigate_services_handles_service_action_exit(_mock_console):
    mock_navigator = Mock()
    mock_navigator.select_service.return_value = "service:web-api"
    mock_navigator.select_service_action.return_value = "navigation:exit"
    mock_ecs_service = Mock()

    result = navigate_services(mock_navigator, mock_ecs_service, "cluster")

    assert result is False


@patch("lazy_ecs.core.app.console")
def test_handle_task_selection_returns_true_when_no_task_details(_mock_console):
    mock_navigator = Mock()
    mock_ecs_service = Mock()
    mock_ecs_service.get_task_details.return_value = None

    result = handle_task_selection(mock_navigator, mock_ecs_service, "cluster", "service", "task-arn")

    assert result is True


@patch("lazy_ecs.core.app.console")
def test_handle_task_selection_calls_handle_task_features(_mock_console):
    mock_navigator = Mock()
    mock_ecs_service = Mock()
    task_details = {"taskArn": "arn:task"}
    mock_ecs_service.get_task_details.return_value = task_details

    with patch("lazy_ecs.core.app.handle_task_features", return_value=True) as mock_handle:
        result = handle_task_selection(mock_navigator, mock_ecs_service, "cluster", "service", "task-arn")

        mock_handle.assert_called_once_with(mock_navigator, "cluster", "task-arn", task_details, "service")
        assert result is True


def test_handle_task_features_returns_true_on_back():
    mock_navigator = Mock()
    mock_navigator.select_task_feature.return_value = "navigation:back"

    assert handle_task_features(mock_navigator, "cluster", "task-arn", None, "service") is True


def test_handle_task_features_returns_false_on_exit():
    mock_navigator = Mock()
    mock_navigator.select_task_feature.return_value = "navigation:exit"

    assert handle_task_features(mock_navigator, "cluster", "task-arn", None, "service") is False


def test_handle_task_features_dispatches_container_action():
    mock_navigator = Mock()
    mock_navigator.select_task_feature.side_effect = ["container_action:show_env:web", "navigation:back"]

    with patch("lazy_ecs.core.app.dispatch_container_action", return_value=True) as mock_dispatch:
        result = handle_task_features(mock_navigator, "cluster", "task-arn", None, "service")

        mock_dispatch.assert_called_once_with(mock_navigator, "cluster", "task-arn", "web", "show_env")
        assert result is True


def test_handle_task_features_dispatches_task_action():
    mock_navigator = Mock()
    mock_navigator.select_task_feature.side_effect = ["task_action:show_history", "navigation:back"]
    task_details = {"taskArn": "arn:task"}

    with patch("lazy_ecs.core.app.dispatch_task_action", return_value=True) as mock_dispatch:
        result = handle_task_features(mock_navigator, "cluster", "task-arn", task_details, "service")  # type: ignore[arg-type]

        mock_dispatch.assert_called_once_with(
            mock_navigator, "cluster", "service", "task-arn", task_details, "show_history"
        )
        assert result is True
