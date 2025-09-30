"""Tests for service UI pagination - fixing the 104 service crash bug."""

from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

from lazy_ecs.features.service.actions import ServiceActions
from lazy_ecs.features.service.service import ServiceService
from lazy_ecs.features.service.ui import ServiceUI


@pytest.fixture
def service_service_with_104_services():
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")
        client.create_cluster(clusterName="production")

        client.register_task_definition(
            family="app-task",
            containerDefinitions=[{"name": "app", "image": "nginx", "memory": 256}],
        )

        for i in range(104):
            client.create_service(
                cluster="production",
                serviceName=f"service-{i:03d}",
                taskDefinition="app-task",
                desiredCount=1,
            )

        yield ServiceService(client)


@patch("lazy_ecs.features.service.ui.select_with_pagination")
def test_select_service_with_104_services_uses_pagination(mock_select_pagination, service_service_with_104_services):
    mock_select_pagination.return_value = "service:service-050"

    service_actions = ServiceActions(service_service_with_104_services.ecs_client)
    service_ui = ServiceUI(service_service_with_104_services, service_actions)

    result = service_ui.select_service("production")

    assert result == "service:service-050"
    mock_select_pagination.assert_called_once()

    call_args = mock_select_pagination.call_args
    choices = call_args[0][1]
    assert len(choices) == 104


@patch("lazy_ecs.features.service.ui.select_with_navigation")
def test_select_service_small_list_uses_shortcuts(mock_select_navigation):
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")
        client.create_cluster(clusterName="production")

        client.register_task_definition(
            family="app-task",
            containerDefinitions=[{"name": "app", "image": "nginx", "memory": 256}],
        )

        for i in range(5):
            client.create_service(
                cluster="production",
                serviceName=f"service-{i}",
                taskDefinition="app-task",
                desiredCount=1,
            )

        service_service = ServiceService(client)
        service_actions = ServiceActions(client)
        mock_select_navigation.return_value = "service:service-2"

        service_ui = ServiceUI(service_service, service_actions)
        result = service_ui.select_service("production")

        assert result == "service:service-2"
        mock_select_navigation.assert_called_once()
