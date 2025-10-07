"""Tests for service service."""

from unittest.mock import Mock

import pytest

from lazy_ecs.features.service.service import ServiceService


@pytest.fixture
def mock_ecs_client(mock_paginated_client):
    pages = [{"serviceArns": []}]
    return mock_paginated_client(pages)


def test_get_service_info_returns_empty_when_no_services(mock_ecs_client):
    service_service = ServiceService(mock_ecs_client)

    result = service_service.get_service_info("cluster")

    assert result == []


def test_get_desired_task_definition_arn_returns_none_when_no_services():
    mock_ecs_client = Mock()
    mock_ecs_client.describe_services.return_value = {"services": []}
    service_service = ServiceService(mock_ecs_client)

    result = service_service.get_desired_task_definition_arn("cluster", "service")

    assert result is None


def test_get_desired_task_definition_arn_success():
    mock_ecs_client = Mock()
    mock_ecs_client.describe_services.return_value = {
        "services": [{"serviceName": "web", "taskDefinition": "arn:task-def:5"}]
    }
    service_service = ServiceService(mock_ecs_client)

    result = service_service.get_desired_task_definition_arn("cluster", "web")

    assert result == "arn:task-def:5"
