"""Tests for UI layer."""

from unittest.mock import Mock, patch

import pytest

from lazy_ecs.ui import ECSNavigator


@pytest.fixture
def mock_ecs_service():
    """Create a mock ECS service."""
    return Mock()


@patch("lazy_ecs.ui.questionary.select")
def test_select_cluster_with_clusters(mock_select, mock_ecs_service) -> None:
    mock_ecs_service.get_cluster_names.return_value = ["production", "staging", "dev"]
    mock_select.return_value.ask.return_value = "production"

    navigator = ECSNavigator(mock_ecs_service)
    selected = navigator.select_cluster()

    assert selected == "production"
    mock_select.assert_called_once()


def test_select_cluster_no_clusters(mock_ecs_service) -> None:
    mock_ecs_service.get_cluster_names.return_value = []

    navigator = ECSNavigator(mock_ecs_service)
    selected = navigator.select_cluster()

    assert selected == ""


@patch("lazy_ecs.ui.questionary.select")
def test_select_service_with_services(mock_select, mock_ecs_service) -> None:
    mock_ecs_service.get_service_info.return_value = [
        {"name": "✅ web-api (2/2)", "status": "HEALTHY", "running_count": 2, "desired_count": 2, "pending_count": 0}
    ]
    mock_select.return_value.ask.return_value = "service:web-api"

    navigator = ECSNavigator(mock_ecs_service)
    selected = navigator.select_service("production")

    assert selected == "service:web-api"
    mock_select.assert_called_once()


def test_select_service_no_services(mock_ecs_service) -> None:
    mock_ecs_service.get_service_info.return_value = []

    navigator = ECSNavigator(mock_ecs_service)
    selected = navigator.select_service("production")

    assert selected == "navigation:back"


@patch("lazy_ecs.ui.questionary.select")
def test_select_service_navigation_back(mock_select, mock_ecs_service) -> None:
    mock_ecs_service.get_service_info.return_value = [
        {"name": "✅ web-api (2/2)", "status": "HEALTHY", "running_count": 2, "desired_count": 2, "pending_count": 0}
    ]
    mock_select.return_value.ask.return_value = "navigation:back"

    navigator = ECSNavigator(mock_ecs_service)
    selected = navigator.select_service("production")

    assert selected == "navigation:back"


def test_select_task_auto_select_single_task(mock_ecs_service) -> None:
    mock_ecs_service.get_task_info.return_value = [{"name": "✅ v1 web-api-task (abc123)", "value": "task-arn-123"}]

    navigator = ECSNavigator(mock_ecs_service)
    selected = navigator.select_task("production", "web-api")

    assert selected == "task-arn-123"


@patch("lazy_ecs.ui.questionary.select")
def test_select_task_multiple_tasks(mock_select, mock_ecs_service) -> None:
    mock_ecs_service.get_task_info.return_value = [
        {"name": "✅ v1 web-api-task (abc123)", "value": "task-arn-123"},
        {"name": "✅ v1 web-api-task (def456)", "value": "task-arn-456"},
    ]
    mock_select.return_value.ask.return_value = "task-arn-123"

    navigator = ECSNavigator(mock_ecs_service)
    selected = navigator.select_task("production", "web-api")

    assert selected == "task-arn-123"
    mock_select.assert_called_once()


def test_select_task_no_tasks(mock_ecs_service) -> None:
    mock_ecs_service.get_task_info.return_value = []

    navigator = ECSNavigator(mock_ecs_service)
    selected = navigator.select_task("production", "web-api")

    assert selected == ""


@patch("lazy_ecs.ui.questionary.select")
def test_select_task_feature_with_containers(mock_select, mock_ecs_service) -> None:
    from lazy_ecs.aws_service import TaskDetails

    mock_select.return_value.ask.return_value = "container_action:show_logs:web"

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

    assert selected == "container_action:show_logs:web"
    mock_select.assert_called_once()


def test_select_task_feature_no_containers(mock_ecs_service) -> None:
    navigator = ECSNavigator(mock_ecs_service)

    selected = navigator.select_task_feature(None)

    assert selected is None


@patch("lazy_ecs.ui.console.print")
def test_show_container_logs_success(mock_print, mock_ecs_service) -> None:
    mock_ecs_service.get_log_config.return_value = {
        "log_group": "/ecs/production/web",
        "log_stream": "ecs/web/task-123",
    }
    mock_ecs_service.get_container_logs.return_value = [
        {"timestamp": 1693766400000, "message": "Starting application"},
        {"timestamp": 1693766401000, "message": "Server listening on port 8080"},
    ]

    navigator = ECSNavigator(mock_ecs_service)
    navigator.show_container_logs("production", "task-arn-123", "web", 50)

    assert mock_print.called
    print_args = [str(call.args[0]) for call in mock_print.call_args_list]
    assert any("log entries" in arg.lower() for arg in print_args)
    assert any("Starting application" in arg for arg in print_args)


@patch("lazy_ecs.ui.console.print")
def test_show_container_logs_no_config(mock_print, mock_ecs_service) -> None:
    mock_ecs_service.get_log_config.return_value = None
    mock_ecs_service.list_log_groups.return_value = ["/ecs/production/web", "/ecs/staging/web"]

    navigator = ECSNavigator(mock_ecs_service)
    navigator.show_container_logs("production", "task-arn-123", "web", 50)

    assert mock_print.called
    print_args = [str(call.args[0]) for call in mock_print.call_args_list]
    assert any("Could not find log configuration" in arg for arg in print_args)


@patch("lazy_ecs.ui.console.print")
def test_show_container_environment_variables_success(mock_print, mock_ecs_service) -> None:
    mock_ecs_service.get_container_environment_variables.return_value = {
        "ENV": "production",
        "DEBUG": "false",
        "DATABASE_URL": "postgres://prod-db:5432/myapp",
    }

    navigator = ECSNavigator(mock_ecs_service)
    navigator.show_container_environment_variables("production", "task-arn-123", "app")

    assert mock_print.called
    print_args = [str(call.args[0]) for call in mock_print.call_args_list]
    assert any("Environment variables" in arg for arg in print_args)
    assert any("ENV=production" in arg for arg in print_args)
    assert any("Total: 3 environment variables" in arg for arg in print_args)


@patch("lazy_ecs.ui.console.print")
def test_show_container_environment_variables_none(mock_print, mock_ecs_service) -> None:
    mock_ecs_service.get_container_environment_variables.return_value = None

    navigator = ECSNavigator(mock_ecs_service)
    navigator.show_container_environment_variables("production", "task-arn-123", "app")

    assert mock_print.called
    print_args = [str(call.args[0]) for call in mock_print.call_args_list]
    assert any("Could not find environment variables" in arg for arg in print_args)


@patch("lazy_ecs.ui.console.print")
def test_show_container_environment_variables_empty(mock_print, mock_ecs_service) -> None:
    mock_ecs_service.get_container_environment_variables.return_value = {}

    navigator = ECSNavigator(mock_ecs_service)
    navigator.show_container_environment_variables("production", "task-arn-123", "app")

    assert mock_print.called
    print_args = [str(call.args[0]) for call in mock_print.call_args_list]
    assert any("No environment variables found" in arg for arg in print_args)


def test_build_task_feature_choices_includes_env_vars() -> None:
    from lazy_ecs.ui import _build_task_feature_choices

    containers = [{"name": "web"}, {"name": "sidecar"}]
    choices = _build_task_feature_choices(containers)

    # Check that we have structured choices
    choice_names = [choice["name"] for choice in choices]
    choice_values = [choice["value"] for choice in choices]

    assert "Show tail of logs for container: web" in choice_names
    assert "Show environment variables for container: web" in choice_names
    assert "Show secrets for container: web" in choice_names
    assert "Show port mappings for container: web" in choice_names
    assert "Show volume mounts for container: web" in choice_names
    assert "Show tail of logs for container: sidecar" in choice_names
    assert "Show environment variables for container: sidecar" in choice_names
    assert "Show volume mounts for container: sidecar" in choice_names
    assert "Show secrets for container: sidecar" in choice_names
    assert "Show port mappings for container: sidecar" in choice_names

    # Check navigation options
    assert "⬅️ Back to service selection" in choice_names
    assert "❌ Exit" in choice_names

    # Check structured values
    assert "container_action:show_logs:web" in choice_values
    assert "container_action:show_env:web" in choice_values
    assert "navigation:back" in choice_values
    assert "navigation:exit" in choice_values

    assert len(choices) == 12  # 10 container actions (5 actions x 2 containers) + 2 navigation


@patch("lazy_ecs.ui.questionary.select")
def test_select_task_feature_navigation_back(mock_select, mock_ecs_service) -> None:
    from lazy_ecs.aws_service import TaskDetails

    mock_select.return_value.ask.return_value = "navigation:back"

    navigator = ECSNavigator(mock_ecs_service)
    task_details: TaskDetails = {
        "task_arn": "task-123",
        "task_definition_name": "web-task",
        "task_definition_revision": "1",
        "is_desired_version": True,
        "task_status": "RUNNING",
        "containers": [{"name": "web"}],
        "created_at": None,
        "started_at": None,
    }

    selected = navigator.select_task_feature(task_details)

    assert selected == "navigation:back"


@patch("lazy_ecs.ui.console.print")
def test_show_container_secrets_success(mock_print, mock_ecs_service) -> None:
    mock_ecs_service.get_container_secrets.return_value = {
        "API_KEY": "arn:aws:secretsmanager:us-east-1:123456789012:secret:api-key-XyZ123",
        "DB_PASSWORD": "arn:aws:ssm:us-east-1:123456789012:parameter/db-password",
        "AUTH_SECRET": "arn:aws:secretsmanager:us-east-1:123456789012:secret:auth-secret",
    }

    navigator = ECSNavigator(mock_ecs_service)
    navigator.show_container_secrets("production", "task-arn-123", "app")

    assert mock_print.called
    print_args = [str(call.args[0]) for call in mock_print.call_args_list]
    assert any("Secrets for container" in arg for arg in print_args)
    assert any("API_KEY → Secrets Manager: api-key-XyZ123" in arg for arg in print_args)
    assert any("DB_PASSWORD → Parameter Store: db-password" in arg for arg in print_args)
    assert any("AUTH_SECRET → Secrets Manager: auth-secret" in arg for arg in print_args)


@patch("lazy_ecs.ui.console.print")
def test_show_container_secrets_none(mock_print, mock_ecs_service) -> None:
    mock_ecs_service.get_container_secrets.return_value = None

    navigator = ECSNavigator(mock_ecs_service)
    navigator.show_container_secrets("production", "task-arn-123", "app")

    assert mock_print.called
    print_args = [str(call.args[0]) for call in mock_print.call_args_list]
    assert any("Could not find secrets configuration" in arg for arg in print_args)


@patch("lazy_ecs.ui.console.print")
def test_show_container_secrets_empty(mock_print, mock_ecs_service) -> None:
    mock_ecs_service.get_container_secrets.return_value = {}

    navigator = ECSNavigator(mock_ecs_service)
    navigator.show_container_secrets("production", "task-arn-123", "app")

    assert mock_print.called
    print_args = [str(call.args[0]) for call in mock_print.call_args_list]
    assert any("No secrets configured" in arg for arg in print_args)


@patch("lazy_ecs.ui.console.print")
def test_show_container_port_mappings_success(mock_print, mock_ecs_service) -> None:
    mock_ecs_service.get_container_port_mappings.return_value = [
        {"containerPort": 80, "hostPort": 8080, "protocol": "tcp"},
        {"containerPort": 443, "hostPort": 0, "protocol": "tcp"},
    ]

    navigator = ECSNavigator(mock_ecs_service)
    navigator.show_container_port_mappings("test-cluster", "task-arn", "web")

    mock_ecs_service.get_container_port_mappings.assert_called_once_with("test-cluster", "task-arn", "web")
    print_args = [str(call.args[0]) for call in mock_print.call_args_list]
    assert any("Port mappings for container 'web'" in arg for arg in print_args)
    assert any("Container:80 → Host:8080 (TCP)" in arg for arg in print_args)
    assert any("Container:443 → Host:dynamic (TCP)" in arg for arg in print_args)


@patch("lazy_ecs.ui.console.print")
def test_show_container_port_mappings_none(mock_print, mock_ecs_service) -> None:
    mock_ecs_service.get_container_port_mappings.return_value = None

    navigator = ECSNavigator(mock_ecs_service)
    navigator.show_container_port_mappings("test-cluster", "task-arn", "web")

    print_args = [str(call.args[0]) for call in mock_print.call_args_list]
    assert any("Could not find port mappings" in arg for arg in print_args)


@patch("lazy_ecs.ui.console.print")
def test_show_container_port_mappings_empty(mock_print, mock_ecs_service) -> None:
    mock_ecs_service.get_container_port_mappings.return_value = []

    navigator = ECSNavigator(mock_ecs_service)
    navigator.show_container_port_mappings("test-cluster", "task-arn", "web")

    print_args = [str(call.args[0]) for call in mock_print.call_args_list]
    assert any("No port mappings configured" in arg for arg in print_args)


@patch("questionary.select")
def test_select_service_action_with_tasks_and_actions(mock_select, mock_ecs_service) -> None:
    mock_ecs_service.get_task_info.return_value = [
        {"name": "task-1", "value": "arn:aws:ecs:us-east-1:123:task/task-1"},
        {"name": "task-2", "value": "arn:aws:ecs:us-east-1:123:task/task-2"},
    ]
    mock_select.return_value.ask.return_value = "task:show_details:arn:aws:ecs:us-east-1:123:task/task-1"

    navigator = ECSNavigator(mock_ecs_service)
    result = navigator.select_service_action("test-cluster", "web-service")

    assert result == "task:show_details:arn:aws:ecs:us-east-1:123:task/task-1"
    mock_select.assert_called_once()


@patch("questionary.select")
def test_select_service_action_force_deployment(mock_select, mock_ecs_service) -> None:
    mock_ecs_service.get_task_info.return_value = [{"name": "task-1", "value": "arn:aws:ecs:us-east-1:123:task/task-1"}]
    mock_select.return_value.ask.return_value = "action:force_deployment"

    navigator = ECSNavigator(mock_ecs_service)
    result = navigator.select_service_action("test-cluster", "web-service")

    assert result == "action:force_deployment"


@patch("lazy_ecs.ui.console.print")
def test_handle_force_deployment_success(mock_print, mock_ecs_service) -> None:
    mock_ecs_service.force_new_deployment.return_value = True

    navigator = ECSNavigator(mock_ecs_service)
    navigator.handle_force_deployment("test-cluster", "web-service")

    mock_ecs_service.force_new_deployment.assert_called_once_with("test-cluster", "web-service")
    print_args = [str(call.args[0]) for call in mock_print.call_args_list]
    assert any("Successfully triggered new deployment" in arg for arg in print_args)


@patch("lazy_ecs.ui.console.print")
def test_handle_force_deployment_failure(mock_print, mock_ecs_service) -> None:
    mock_ecs_service.force_new_deployment.return_value = False

    navigator = ECSNavigator(mock_ecs_service)
    navigator.handle_force_deployment("test-cluster", "web-service")

    print_args = [str(call.args[0]) for call in mock_print.call_args_list]
    assert any("Failed to force new deployment" in arg for arg in print_args)


def test_show_container_volume_mounts_success(mock_ecs_service, capsys) -> None:
    mock_ecs_service.get_container_volume_mounts.return_value = [
        {
            "source_volume": "data-volume",
            "container_path": "/app/data",
            "read_only": False,
            "host_path": "/opt/data",
        },
        {
            "source_volume": "logs-volume",
            "container_path": "/app/logs",
            "read_only": False,
            "host_path": "/var/log/app",
        },
        {
            "source_volume": "config-volume",
            "container_path": "/app/config",
            "read_only": True,
            "host_path": None,
        },
    ]

    navigator = ECSNavigator(mock_ecs_service)
    navigator.show_container_volume_mounts("test-cluster", "task-arn", "web")

    captured = capsys.readouterr()
    assert "Volume mounts for container 'web':" in captured.out
    assert "data-volume" in captured.out
    assert "/app/data" in captured.out
    assert "/opt/data" in captured.out
    assert "read-write" in captured.out
    assert "logs-volume" in captured.out
    assert "/app/logs" in captured.out
    assert "/var/log/app" in captured.out
    assert "config-volume" in captured.out
    assert "/app/config" in captured.out
    assert "read-only" in captured.out
    assert "Empty volume" in captured.out
    assert "Total: 3 volume mounts" in captured.out


def test_show_container_volume_mounts_none(mock_ecs_service, capsys) -> None:
    mock_ecs_service.get_container_volume_mounts.return_value = None

    navigator = ECSNavigator(mock_ecs_service)
    navigator.show_container_volume_mounts("test-cluster", "task-arn", "web")

    captured = capsys.readouterr()
    assert "Could not find volume mounts for container 'web'" in captured.out


def test_show_container_volume_mounts_empty(mock_ecs_service, capsys) -> None:
    mock_ecs_service.get_container_volume_mounts.return_value = []

    navigator = ECSNavigator(mock_ecs_service)
    navigator.show_container_volume_mounts("test-cluster", "task-arn", "web")

    captured = capsys.readouterr()
    assert "No volume mounts configured for container 'web'" in captured.out
