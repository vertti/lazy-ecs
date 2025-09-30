"""Tests for ContainerUI class."""

from collections.abc import Generator
from datetime import datetime
from typing import Any, cast
from unittest.mock import Mock, call, patch

import pytest

from lazy_ecs.features.container.container import ContainerService
from lazy_ecs.features.container.ui import ContainerUI


@pytest.fixture
def mock_ecs_client():
    return Mock()


@pytest.fixture
def mock_task_service():
    return Mock()


@pytest.fixture
def container_ui(mock_ecs_client, mock_task_service):
    container_service = ContainerService(mock_ecs_client, mock_task_service)
    return ContainerUI(container_service)


def test_show_container_logs_success(container_ui):
    """Test displaying container logs successfully."""
    log_config = {"log_group": "test-log-group", "log_stream": "test-stream"}
    events = [
        {"timestamp": 1234567890000, "message": "Test log message 1"},
        {"timestamp": 1234567891000, "message": "Test log message 2"},
    ]

    container_ui.container_service.get_log_config = Mock(return_value=log_config)
    container_ui.container_service.get_container_logs = Mock(return_value=events)

    container_ui.show_container_logs("test-cluster", "task-arn", "web-container", 50)

    container_ui.container_service.get_log_config.assert_called_once_with("test-cluster", "task-arn", "web-container")
    container_ui.container_service.get_container_logs.assert_called_once_with("test-log-group", "test-stream", 50)


def test_show_logs_live_tail_success(container_ui):
    """Test displaying live tail container logs successfully."""
    log_config = {"log_group": "test-log-group", "log_stream": "test-stream"}
    events = [
        {"eventId": "event1", "timestamp": 1234567890000, "message": "Live tail log message 1"},
        {"eventId": "event2", "timestamp": 1234567891000, "message": "Live tail log message 2"},
        {"eventId": "event3", "timestamp": 1234567892000, "message": "Live tail log message 3"},
        {"eventId": "event4", "timestamp": 1234567893000, "message": "Live tail log message 4"},
    ]

    container_ui.container_service.get_log_config = Mock(return_value=log_config)
    container_ui.container_service.get_live_container_logs_tail = Mock(return_value=iter(events))

    with patch("rich.console.Console.print") as mock_console_print:
        container_ui.show_logs_live_tail("test-cluster", "task-arn", "web-container")

    container_ui.container_service.get_log_config.assert_called_once_with("test-cluster", "task-arn", "web-container")
    container_ui.container_service.get_live_container_logs_tail.assert_called_once_with("test-log-group", "test-stream")

    expected_calls = [
        call("\n🚀 Tailing logs for container 'web-container':", style="bold cyan"),
        call("log group: test-log-group", style="dim"),
        call("log stream: test-stream", style="dim"),
        call("Press Ctrl+C to stop.", style="dim"),
        call("=" * 80, style="dim"),
    ]

    for event in events:
        timestamp = cast(int, event["timestamp"])
        dt = datetime.fromtimestamp(timestamp / 1000)
        message = cast(str, event["message"]).rstrip()
        expected_calls.append(call(f"[{dt.strftime('%H:%M:%S')}] {message}"))

    expected_calls.append(call("=" * 80, style="dim"))
    mock_console_print.assert_has_calls(expected_calls, any_order=False)


def test_show_logs_live_tail_keyboard_interrupt(container_ui):
    """Test handling keyboard interruptions with Ctrl+C during live logs tail."""
    log_config = {"log_group": "test-log-group", "log_stream": "test-stream"}

    def mock_generator() -> Generator[dict[str, Any], None, None]:
        yield {"eventId": "event1", "timestamp": 1234567890000, "message": "Live tail log message 1"}
        raise KeyboardInterrupt()

    container_ui.container_service.get_log_config = Mock(return_value=log_config)
    container_ui.container_service.get_live_container_logs_tail = Mock(return_value=mock_generator())

    with patch("rich.console.Console.print") as mock_console_print:
        container_ui.show_logs_live_tail("test-cluster", "task-arn", "web-container")

    mock_console_print.assert_any_call("\n🛑 Stopped tailing logs.", style="yellow")


def test_show_logs_live_tail_no_config(container_ui):
    """Test displaying live tail container logs with no log configuration."""
    container_ui.container_service.get_log_config = Mock(return_value=None)
    container_ui.container_service.list_log_groups = Mock(return_value=["group1", "group2"])

    with (
        patch("lazy_ecs.features.container.ui.print_error") as mock_print_error,
        patch("rich.console.Console.print") as mock_console_print,
    ):
        container_ui.show_logs_live_tail("test-cluster", "task-arn", "web-container")

    mock_print_error.assert_called_once_with("Could not find log configuration for container 'web-container'")
    mock_console_print.assert_any_call("Available log groups:", style="dim")


def test_show_container_logs_no_config(container_ui):
    """Test displaying container logs with no log configuration."""
    container_ui.container_service.get_log_config = Mock(return_value=None)
    container_ui.container_service.list_log_groups = Mock(return_value=["group1", "group2"])

    container_ui.show_container_logs("test-cluster", "task-arn", "web-container", 50)

    container_ui.container_service.get_log_config.assert_called_once_with("test-cluster", "task-arn", "web-container")
    container_ui.container_service.list_log_groups.assert_called_once_with("test-cluster", "web-container")


def test_show_container_logs_no_events(container_ui):
    """Test displaying container logs with no events."""
    log_config = {"log_group": "test-log-group", "log_stream": "test-stream"}

    container_ui.container_service.get_log_config = Mock(return_value=log_config)
    container_ui.container_service.get_container_logs = Mock(return_value=[])

    container_ui.show_container_logs("test-cluster", "task-arn", "web-container", 50)

    container_ui.container_service.get_log_config.assert_called_once_with("test-cluster", "task-arn", "web-container")
    container_ui.container_service.get_container_logs.assert_called_once_with("test-log-group", "test-stream", 50)


def test_show_container_environment_variables_success(container_ui):
    """Test displaying container environment variables successfully."""
    context = {"container_definition": {"environment": [{"name": "ENV_VAR", "value": "value"}]}}
    env_vars = {"ENV_VAR": "value", "ANOTHER_VAR": "another_value"}

    container_ui.container_service.get_container_context = Mock(return_value=context)
    container_ui.container_service.get_environment_variables = Mock(return_value=env_vars)

    container_ui.show_container_environment_variables("test-cluster", "task-arn", "web-container")

    container_ui.container_service.get_container_context.assert_called_once_with(
        "test-cluster", "task-arn", "web-container"
    )
    container_ui.container_service.get_environment_variables.assert_called_once_with(context)


def test_show_container_environment_variables_no_context(container_ui):
    """Test displaying environment variables with no container context."""
    container_ui.container_service.get_container_context = Mock(return_value=None)

    container_ui.show_container_environment_variables("test-cluster", "task-arn", "web-container")

    container_ui.container_service.get_container_context.assert_called_once_with(
        "test-cluster", "task-arn", "web-container"
    )


def test_show_container_environment_variables_empty(container_ui):
    """Test displaying container environment variables when empty."""
    context = {"container_definition": {"environment": []}}

    container_ui.container_service.get_container_context = Mock(return_value=context)
    container_ui.container_service.get_environment_variables = Mock(return_value={})

    container_ui.show_container_environment_variables("test-cluster", "task-arn", "web-container")

    container_ui.container_service.get_container_context.assert_called_once_with(
        "test-cluster", "task-arn", "web-container"
    )
    container_ui.container_service.get_environment_variables.assert_called_once_with(context)


def test_show_container_secrets_success(container_ui):
    """Test displaying container secrets successfully."""
    context = {"container_definition": {"secrets": []}}
    secrets = {
        "SECRET_KEY": "arn:aws:secretsmanager:us-east-1:123:secret:test",
        "PARAM_KEY": "arn:aws:ssm:us-east-1:123:parameter/test",
    }

    container_ui.container_service.get_container_context = Mock(return_value=context)
    container_ui.container_service.get_secrets = Mock(return_value=secrets)

    container_ui.show_container_secrets("test-cluster", "task-arn", "web-container")

    container_ui.container_service.get_container_context.assert_called_once_with(
        "test-cluster", "task-arn", "web-container"
    )
    container_ui.container_service.get_secrets.assert_called_once_with(context)


def test_show_container_secrets_no_context(container_ui):
    """Test displaying secrets with no container context."""
    container_ui.container_service.get_container_context = Mock(return_value=None)

    container_ui.show_container_secrets("test-cluster", "task-arn", "web-container")

    container_ui.container_service.get_container_context.assert_called_once_with(
        "test-cluster", "task-arn", "web-container"
    )


def test_show_container_secrets_empty(container_ui):
    """Test displaying container secrets when empty."""
    context = {"container_definition": {"secrets": []}}

    container_ui.container_service.get_container_context = Mock(return_value=context)
    container_ui.container_service.get_secrets = Mock(return_value={})

    container_ui.show_container_secrets("test-cluster", "task-arn", "web-container")

    container_ui.container_service.get_container_context.assert_called_once_with(
        "test-cluster", "task-arn", "web-container"
    )
    container_ui.container_service.get_secrets.assert_called_once_with(context)


def test_show_container_port_mappings_success(container_ui):
    """Test displaying container port mappings successfully."""
    context = {"container_definition": {"portMappings": []}}
    port_mappings = [{"containerPort": 8080, "hostPort": 80, "protocol": "tcp"}]

    container_ui.container_service.get_container_context = Mock(return_value=context)
    container_ui.container_service.get_port_mappings = Mock(return_value=port_mappings)

    container_ui.show_container_port_mappings("test-cluster", "task-arn", "web-container")

    container_ui.container_service.get_container_context.assert_called_once_with(
        "test-cluster", "task-arn", "web-container"
    )
    container_ui.container_service.get_port_mappings.assert_called_once_with(context)


def test_show_container_port_mappings_no_context(container_ui):
    """Test displaying port mappings with no container context."""
    container_ui.container_service.get_container_context = Mock(return_value=None)

    container_ui.show_container_port_mappings("test-cluster", "task-arn", "web-container")

    container_ui.container_service.get_container_context.assert_called_once_with(
        "test-cluster", "task-arn", "web-container"
    )


def test_show_container_port_mappings_empty(container_ui):
    """Test displaying container port mappings when empty."""
    context = {"container_definition": {"portMappings": []}}

    container_ui.container_service.get_container_context = Mock(return_value=context)
    container_ui.container_service.get_port_mappings = Mock(return_value=[])

    container_ui.show_container_port_mappings("test-cluster", "task-arn", "web-container")

    container_ui.container_service.get_container_context.assert_called_once_with(
        "test-cluster", "task-arn", "web-container"
    )
    container_ui.container_service.get_port_mappings.assert_called_once_with(context)


def test_show_container_volume_mounts_success(container_ui):
    """Test displaying container volume mounts successfully."""
    context = {"container_definition": {"mountPoints": []}}
    volume_mounts = [
        {"source_volume": "data-vol", "container_path": "/data", "read_only": False, "host_path": "/host/data"}
    ]

    container_ui.container_service.get_container_context = Mock(return_value=context)
    container_ui.container_service.get_volume_mounts = Mock(return_value=volume_mounts)

    container_ui.show_container_volume_mounts("test-cluster", "task-arn", "web-container")

    container_ui.container_service.get_container_context.assert_called_once_with(
        "test-cluster", "task-arn", "web-container"
    )
    container_ui.container_service.get_volume_mounts.assert_called_once_with(context)


def test_show_container_volume_mounts_no_context(container_ui):
    """Test displaying volume mounts with no container context."""
    container_ui.container_service.get_container_context = Mock(return_value=None)

    container_ui.show_container_volume_mounts("test-cluster", "task-arn", "web-container")

    container_ui.container_service.get_container_context.assert_called_once_with(
        "test-cluster", "task-arn", "web-container"
    )


def test_show_container_volume_mounts_empty(container_ui):
    """Test displaying container volume mounts when empty."""
    context = {"container_definition": {"mountPoints": []}}

    container_ui.container_service.get_container_context = Mock(return_value=context)
    container_ui.container_service.get_volume_mounts = Mock(return_value=[])

    container_ui.show_container_volume_mounts("test-cluster", "task-arn", "web-container")

    container_ui.container_service.get_container_context.assert_called_once_with(
        "test-cluster", "task-arn", "web-container"
    )
    container_ui.container_service.get_volume_mounts.assert_called_once_with(context)
