"""Tests for ContainerUI class."""

from unittest.mock import Mock

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
