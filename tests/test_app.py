"""Tests for core application logic."""

from unittest.mock import Mock

from lazy_ecs.core.app import (
    dispatch_container_action,
    dispatch_service_action,
    dispatch_task_action,
    get_container_action_handlers,
    get_service_action_handlers,
    get_task_action_handlers,
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
