"""Tests for container service functions."""

from unittest.mock import Mock

import pytest

from lazy_ecs.features.container.container import ContainerService


@pytest.fixture
def mock_task_service():
    return Mock()


@pytest.fixture
def container_service(mock_task_service):
    mock_ecs_client = Mock()
    return ContainerService(mock_ecs_client, mock_task_service)


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
