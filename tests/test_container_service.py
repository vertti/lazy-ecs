"""Tests for container service functions."""

from unittest.mock import Mock

import pytest

from lazy_ecs.features.container.container import ContainerService, build_log_group_arn, build_log_stream_name


@pytest.fixture
def mock_task_service():
    return Mock()


@pytest.fixture
def container_service(mock_task_service):
    mock_ecs_client = Mock()
    return ContainerService(mock_ecs_client, mock_task_service)


@pytest.fixture
def mock_task_with_awslogs():
    return {
        "taskArn": "arn:aws:ecs:us-east-1:123:task/cluster/abc123",
        "taskDefinitionArn": "arn:task-def:1",
    }


@pytest.fixture
def mock_task_definition_with_awslogs():
    return {
        "containerDefinitions": [
            {
                "name": "web",
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {"awslogs-group": "/ecs/my-app"},
                },
            }
        ]
    }


def test_get_container_context_returns_none_when_task_not_found(container_service, mock_task_service):
    mock_task_service.get_task_and_definition.return_value = None

    result = container_service.get_container_context("cluster", "task-arn", "container-name")

    assert result is None


def test_get_container_context_returns_none_when_container_not_found(container_service, mock_task_service):
    mock_task = {"taskArn": "task-arn"}
    mock_task_definition = {
        "containerDefinitions": [
            {"name": "other-container", "image": "nginx:latest"},
        ]
    }
    mock_task_service.get_task_and_definition.return_value = (mock_task, mock_task_definition)

    result = container_service.get_container_context("cluster", "task-arn", "missing-container")

    assert result is None


def test_get_container_context_success(container_service, mock_task_service):
    mock_task = {"taskArn": "task-arn"}
    mock_task_definition = {
        "containerDefinitions": [
            {"name": "web", "image": "nginx:latest"},
        ]
    }
    mock_task_service.get_task_and_definition.return_value = (mock_task, mock_task_definition)

    result = container_service.get_container_context("cluster", "task-arn", "web")

    assert result.container_name == "web"
    assert result.cluster_name == "cluster"
    assert result.task_arn == "task-arn"


def test_get_container_definition_not_found(container_service):
    task_definition = {
        "containerDefinitions": [
            {"name": "web", "image": "nginx:latest"},
        ]
    }

    result = container_service.get_container_definition(task_definition, "missing")

    assert result is None


def test_get_container_definition_success(container_service):
    task_definition = {
        "containerDefinitions": [
            {"name": "web", "image": "nginx:latest"},
            {"name": "worker", "image": "python:3.11"},
        ]
    }

    result = container_service.get_container_definition(task_definition, "worker")

    assert result["name"] == "worker"
    assert result["image"] == "python:3.11"


def test_build_log_group_arn():
    arn = build_log_group_arn("us-east-1", "123456789012", "my-log-group")

    assert arn == "arn:aws:logs:us-east-1:123456789012:log-group:my-log-group"


def test_build_log_stream_name():
    stream = build_log_stream_name("ecs", "web-container", "abc123def456")

    assert stream == "ecs/web-container/abc123def456"


def test_build_log_stream_name_with_custom_prefix():
    stream = build_log_stream_name("my-app", "worker", "task-id-123")

    assert stream == "my-app/worker/task-id-123"


def test_get_log_config_returns_none_when_context_not_found(container_service, mock_task_service):
    mock_task_service.get_task_and_definition.return_value = None

    result = container_service.get_log_config("cluster", "task-arn", "container")

    assert result is None


def test_get_log_config_returns_none_for_non_awslogs_driver(
    container_service, mock_task_service, mock_task_with_awslogs
):
    mock_task_definition = {"containerDefinitions": [{"name": "web", "logConfiguration": {"logDriver": "splunk"}}]}
    mock_task_service.get_task_and_definition.return_value = (mock_task_with_awslogs, mock_task_definition)

    result = container_service.get_log_config("cluster", "task-arn", "web")

    assert result is None


def test_get_log_config_returns_none_when_no_log_group(container_service, mock_task_service, mock_task_with_awslogs):
    mock_task_definition = {
        "containerDefinitions": [{"name": "web", "logConfiguration": {"logDriver": "awslogs", "options": {}}}]
    }
    mock_task_service.get_task_and_definition.return_value = (mock_task_with_awslogs, mock_task_definition)

    result = container_service.get_log_config("cluster", "task-arn", "web")

    assert result is None


def test_get_log_config_success_with_defaults(
    container_service, mock_task_service, mock_task_with_awslogs, mock_task_definition_with_awslogs
):
    mock_task_service.get_task_and_definition.return_value = (mock_task_with_awslogs, mock_task_definition_with_awslogs)

    result = container_service.get_log_config("cluster", "arn:aws:ecs:us-east-1:123:task/cluster/abc123", "web")

    assert result["log_group"] == "/ecs/my-app"
    assert result["log_stream"] == "ecs/web/abc123"


def test_get_log_config_success_with_custom_prefix(container_service, mock_task_service):
    mock_task = {"taskArn": "arn:aws:ecs:us-east-1:123:task/cluster/task-id-456"}
    mock_task_definition = {
        "containerDefinitions": [
            {
                "name": "worker",
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {"awslogs-group": "/ecs/workers", "awslogs-stream-prefix": "app"},
                },
            }
        ]
    }
    mock_task_service.get_task_and_definition.return_value = (mock_task, mock_task_definition)

    result = container_service.get_log_config("cluster", "arn:aws:ecs:us-east-1:123:task/cluster/task-id-456", "worker")

    assert result["log_group"] == "/ecs/workers"
    assert result["log_stream"] == "app/worker/task-id-456"


def test_get_container_logs_returns_empty_when_no_client(mock_task_service):
    container_service = ContainerService(Mock(), mock_task_service, logs_client=None)

    result = container_service.get_container_logs("/ecs/app", "stream")

    assert result == []


def test_get_container_logs_success():
    mock_logs_client = Mock()
    mock_logs_client.get_log_events.return_value = {"events": [{"message": "log1"}, {"message": "log2"}]}
    container_service = ContainerService(Mock(), Mock(), logs_client=mock_logs_client)

    result = container_service.get_container_logs("/ecs/app", "stream", lines=100)

    assert len(result) == 2
    mock_logs_client.get_log_events.assert_called_once_with(
        logGroupName="/ecs/app", logStreamName="stream", limit=100, startFromHead=False
    )


def test_get_container_logs_filtered_returns_empty_when_no_client(mock_task_service):
    container_service = ContainerService(Mock(), mock_task_service, logs_client=None)

    result = container_service.get_container_logs_filtered("/ecs/app", "stream", "ERROR")

    assert result == []


def test_get_container_logs_filtered_success():
    mock_logs_client = Mock()
    mock_logs_client.filter_log_events.return_value = {"events": [{"message": "ERROR: failed"}]}
    container_service = ContainerService(Mock(), Mock(), logs_client=mock_logs_client)

    result = container_service.get_container_logs_filtered("/ecs/app", "stream", "ERROR", lines=25)

    assert len(result) == 1
    mock_logs_client.filter_log_events.assert_called_once_with(
        logGroupName="/ecs/app", logStreamNames=["stream"], filterPattern="ERROR", limit=25
    )


def test_list_log_groups_returns_empty_when_no_client(mock_task_service):
    container_service = ContainerService(Mock(), mock_task_service, logs_client=None)

    result = container_service.list_log_groups("production", "web")

    assert result == []


def test_list_log_groups_filters_by_cluster_and_container():
    mock_logs_client = Mock()
    mock_logs_client.describe_log_groups.return_value = {
        "logGroups": [
            {"logGroupName": "/ecs/production-web"},
            {"logGroupName": "/ecs/staging-api"},
            {"logGroupName": "/aws/lambda/function"},
            {"logGroupName": "/ecs/production-worker"},
        ]
    }
    container_service = ContainerService(Mock(), Mock(), logs_client=mock_logs_client)

    result = container_service.list_log_groups("production", "web")

    assert "/ecs/production-web" in result
    assert "/ecs/staging-api" in result  # Contains "ecs" so it's included
