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
    mock_select.return_value.ask.return_value = "web-api"

    navigator = ECSNavigator(mock_ecs_service)
    selected = navigator.select_service("production")

    assert selected == "web-api"
    mock_select.assert_called_once()


def test_select_service_no_services(mock_ecs_service) -> None:
    mock_ecs_service.get_service_info.return_value = []

    navigator = ECSNavigator(mock_ecs_service)
    selected = navigator.select_service("production")

    assert selected == ""


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

    mock_select.return_value.ask.return_value = "Show tail of logs for container: web"

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

    assert selected == "Show tail of logs for container: web"
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

    assert "Show tail of logs for container: web" in choices
    assert "Show environment variables for container: web" in choices
    assert "Show secrets for container: web" in choices
    assert "Show port mappings for container: web" in choices
    assert "Show tail of logs for container: sidecar" in choices
    assert "Show environment variables for container: sidecar" in choices
    assert "Show secrets for container: sidecar" in choices
    assert "Show port mappings for container: sidecar" in choices
    assert "Exit" in choices
    assert len(choices) == 9


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
