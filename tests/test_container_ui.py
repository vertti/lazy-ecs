"""Tests for ContainerUI class."""

import queue
from unittest.mock import Mock, patch

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
def mock_container_context():
    return Mock(
        cluster_name="test-cluster",
        task_arn="test-task-arn",
        container_name="test-container",
        container_definition={
            "name": "test-container",
            "healthCheck": {
                "command": ["CMD-SHELL", "curl -f http://localhost/health || exit 1"],
                "interval": 30,
                "timeout": 5,
                "retries": 3,
                "startPeriod": 60,
            },
        },
    )


@pytest.fixture
def container_ui(mock_ecs_client, mock_task_service):
    container_service = ContainerService(mock_ecs_client, mock_task_service)
    return ContainerUI(container_service)


def test_show_logs_live_tail_with_stop(container_ui):
    """Test displaying logs and stopping immediately."""
    log_config = {"log_group": "test-log-group", "log_stream": "test-stream"}
    recent_events = [
        {"timestamp": 1234567888000, "message": "Recent log message 1"},
    ]

    live_events = [
        {"eventId": "event1", "timestamp": 1234567890000, "message": "Live message"},
    ]

    container_ui.container_service.get_log_config = Mock(return_value=log_config)
    container_ui.container_service.get_container_logs = Mock(return_value=recent_events)
    container_ui.container_service.get_live_container_logs_tail = Mock(return_value=iter(live_events))

    # Mock the queues to immediately provide 's' key
    with (
        patch("lazy_ecs.features.container.ui.queue.Queue") as mock_queue_class,
        patch("lazy_ecs.features.container.ui.threading.Thread"),
        patch("rich.console.Console.print"),
    ):
        key_queue = Mock()
        log_queue = Mock()

        # Key queue: First call returns False (has key), subsequent calls return True (empty)
        key_queue.empty.side_effect = [False, True, True, True, True]
        key_queue.get_nowait.return_value = "s"  # KEY_STOP

        # Log queue: Always empty for this test (we just want to stop immediately)
        log_queue.get_nowait.side_effect = queue.Empty()

        # Return different queue instances for key_queue and log_queue
        mock_queue_class.side_effect = [key_queue, log_queue]

        container_ui.show_logs_live_tail("test-cluster", "task-arn", "web-container")

    container_ui.container_service.get_log_config.assert_called_once_with("test-cluster", "task-arn", "web-container")


def test_show_logs_live_tail_with_filter_exclude(container_ui):
    """Test filter with exclude patterns during log tailing."""
    log_config = {"log_group": "test-log-group", "log_stream": "test-stream"}
    recent_events = [
        {"timestamp": 1234567888000, "message": "Normal message"},
    ]
    filtered_events = [
        {"timestamp": 1234567889000, "message": "Another message"},
    ]
    live_events_first = [
        {"eventId": "event1", "timestamp": 1234567890000, "message": "Live message"},
    ]
    live_events_second = [
        {"eventId": "event2", "timestamp": 1234567891000, "message": "Second live message"},
    ]

    container_ui.container_service.get_log_config = Mock(return_value=log_config)
    container_ui.container_service.get_container_logs = Mock(return_value=recent_events)
    container_ui.container_service.get_container_logs_filtered = Mock(return_value=filtered_events)
    # Return different iterators for each call
    container_ui.container_service.get_live_container_logs_tail = Mock(
        side_effect=[iter(live_events_first), iter(live_events_second)]
    )

    # Mock the queues to simulate pressing 'f' for filter then 's' to stop
    with (
        patch("rich.console.Console.input") as mock_input,
        patch("lazy_ecs.features.container.ui.queue.Queue") as mock_queue_class,
        patch("lazy_ecs.features.container.ui.threading.Thread"),
        patch("rich.console.Console.print"),
    ):
        mock_input.return_value = "-healthcheck"  # Exclude pattern

        key_queue = Mock()
        log_queue = Mock()

        # Key queue: First iteration return 'f', clear queue, then later return 's'
        key_queue.empty.side_effect = [False, True, True, True, False, True, True, True]
        key_queue.get_nowait.side_effect = ["f", queue.Empty(), "s"]  # KEY_FILTER then KEY_STOP

        # Log queue: Always empty for simplicity
        log_queue.get_nowait.side_effect = queue.Empty()

        # Return queue instances: First call for key_queue, second for log_queue
        # Then again for the second iteration after 'f' is pressed
        mock_queue_class.side_effect = [key_queue, log_queue, key_queue, log_queue]

        container_ui.show_logs_live_tail("test-cluster", "task-arn", "web-container")

    # Should be called with -healthcheck filter pattern
    container_ui.container_service.get_container_logs_filtered.assert_called_once_with(
        "test-log-group", "test-stream", "-healthcheck", 50
    )


def test_show_logs_live_tail_no_config(container_ui):
    """Test displaying live tail container logs with no log configuration."""
    container_ui.container_service.get_log_config = Mock(return_value=None)
    container_ui.container_service.list_log_groups = Mock(return_value=["group1", "group2"])

    with patch("lazy_ecs.features.container.ui.print_error") as mock_print_error:
        container_ui.show_logs_live_tail("test-cluster", "task-arn", "web-container")

    mock_print_error.assert_called_once_with("Could not find log configuration for container 'web-container'")


def test_get_container_logs_filtered(mock_ecs_client, mock_task_service):
    """Test filtering container logs with CloudWatch pattern."""
    mock_logs_client = Mock()
    mock_logs_client.filter_log_events.return_value = {
        "events": [
            {"timestamp": 1234567890000, "message": "ERROR: Something failed"},
        ]
    }

    container_service = ContainerService(mock_ecs_client, mock_task_service, None, mock_logs_client)
    events = container_service.get_container_logs_filtered("test-log-group", "test-stream", "ERROR", 50)

    assert len(events) == 1
    assert "ERROR" in events[0]["message"]
    mock_logs_client.filter_log_events.assert_called_once_with(
        logGroupName="test-log-group",
        logStreamNames=["test-stream"],
        filterPattern="ERROR",
        limit=50,
    )


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


def test_get_health_check_config_with_config(mock_ecs_client, mock_task_service, mock_container_context):
    """Test getting health check configuration when present."""
    container_service = ContainerService(mock_ecs_client, mock_task_service)

    config = container_service.get_health_check_config(mock_container_context)

    assert config is not None
    assert config["command"] == ["CMD-SHELL", "curl -f http://localhost/health || exit 1"]
    assert config["interval"] == 30
    assert config["timeout"] == 5
    assert config["retries"] == 3
    assert config["start_period"] == 60


def test_get_health_check_config_no_config(mock_ecs_client, mock_task_service):
    """Test getting health check configuration when not present."""
    container_service = ContainerService(mock_ecs_client, mock_task_service)
    context = Mock(container_definition={"name": "test-container"})

    config = container_service.get_health_check_config(context)

    assert config is None


def test_get_health_status(mock_ecs_client, mock_task_service):
    """Test getting current health status from running task."""
    mock_ecs_client.describe_tasks.return_value = {
        "tasks": [{"containers": [{"name": "test-container", "healthStatus": "HEALTHY"}]}]
    }

    container_service = ContainerService(mock_ecs_client, mock_task_service)
    status = container_service.get_health_status("test-cluster", "test-task-arn", "test-container")

    assert status == "HEALTHY"
    mock_ecs_client.describe_tasks.assert_called_once_with(cluster="test-cluster", tasks=["test-task-arn"])


def test_get_health_status_container_not_found(mock_ecs_client, mock_task_service):
    """Test getting health status when container not found."""
    mock_ecs_client.describe_tasks.return_value = {
        "tasks": [{"containers": [{"name": "other-container", "healthStatus": "HEALTHY"}]}]
    }

    container_service = ContainerService(mock_ecs_client, mock_task_service)
    status = container_service.get_health_status("test-cluster", "test-task-arn", "test-container")

    assert status == "UNKNOWN"


def test_show_container_health_check_with_config(container_ui, mock_container_context):
    """Test displaying health check configuration and status."""
    health_config = {
        "command": ["CMD-SHELL", "curl -f http://localhost/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "start_period": 60,
    }

    container_ui.container_service.get_container_context = Mock(return_value=mock_container_context)
    container_ui.container_service.get_health_check_config = Mock(return_value=health_config)
    container_ui.container_service.get_health_status = Mock(return_value="HEALTHY")

    container_ui.show_container_health_check("test-cluster", "test-task-arn", "test-container")

    container_ui.container_service.get_container_context.assert_called_once_with(
        "test-cluster", "test-task-arn", "test-container"
    )
    container_ui.container_service.get_health_check_config.assert_called_once_with(mock_container_context)
    container_ui.container_service.get_health_status.assert_called_once_with(
        "test-cluster", "test-task-arn", "test-container"
    )


def test_show_container_health_check_no_context(container_ui):
    """Test displaying health check with no container context."""
    container_ui.container_service.get_container_context = Mock(return_value=None)

    container_ui.show_container_health_check("test-cluster", "test-task-arn", "test-container")

    container_ui.container_service.get_container_context.assert_called_once_with(
        "test-cluster", "test-task-arn", "test-container"
    )


def test_show_container_health_check_no_config(container_ui, mock_container_context):
    """Test displaying health check when no configuration present."""
    container_ui.container_service.get_container_context = Mock(return_value=mock_container_context)
    container_ui.container_service.get_health_check_config = Mock(return_value=None)

    container_ui.show_container_health_check("test-cluster", "test-task-arn", "test-container")

    container_ui.container_service.get_health_check_config.assert_called_once_with(mock_container_context)
