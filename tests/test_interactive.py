from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

from lazy_ecs.interactive import ECSNavigator


@pytest.fixture
def ecs_client_with_clusters():
    """Create a mocked ECS client with test clusters."""
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")

        # Create test clusters
        client.create_cluster(clusterName="production")
        client.create_cluster(clusterName="staging")
        client.create_cluster(clusterName="dev")

        yield client


@pytest.fixture
def ecs_client_empty():
    """Create a mocked ECS client with no clusters."""
    with mock_aws():
        yield boto3.client("ecs", region_name="us-east-1")


def test_get_cluster_names(ecs_client_with_clusters):
    navigator = ECSNavigator(ecs_client_with_clusters)
    clusters = navigator.get_cluster_names()

    expected = ["production", "staging", "dev"]
    assert sorted(clusters) == sorted(expected)


@patch("lazy_ecs.interactive.questionary.select")
def test_select_cluster_interactive(mock_select, ecs_client_with_clusters):
    mock_select.return_value.ask.return_value = "production"

    navigator = ECSNavigator(ecs_client_with_clusters)
    selected = navigator.select_cluster()

    assert selected == "production"
    mock_select.assert_called_once()


def test_cluster_selection_with_no_clusters(ecs_client_empty):
    navigator = ECSNavigator(ecs_client_empty)
    clusters = navigator.get_cluster_names()

    assert clusters == []


@patch("lazy_ecs.interactive.questionary.select")
def test_select_cluster_interactive_no_clusters(mock_select, ecs_client_empty):
    navigator = ECSNavigator(ecs_client_empty)
    selected = navigator.select_cluster()

    assert selected == ""
    mock_select.assert_not_called()


@pytest.fixture
def ecs_client_with_services():
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")

        client.create_cluster(clusterName="production")

        # Create task definitions first (required for services)
        client.register_task_definition(
            family="web-api-task",
            containerDefinitions=[{"name": "web", "image": "nginx", "memory": 256}],
        )
        client.register_task_definition(
            family="worker-task",
            containerDefinitions=[{"name": "worker", "image": "worker", "memory": 256}],
        )
        client.register_task_definition(
            family="db-proxy-task",
            containerDefinitions=[{"name": "proxy", "image": "proxy", "memory": 256}],
        )

        # Now create services
        client.create_service(
            cluster="production", serviceName="web-api", taskDefinition="web-api-task"
        )
        client.create_service(
            cluster="production",
            serviceName="worker-service",
            taskDefinition="worker-task",
        )
        client.create_service(
            cluster="production",
            serviceName="database-proxy",
            taskDefinition="db-proxy-task",
        )

        yield client


def test_get_services_from_cluster(ecs_client_with_services):
    navigator = ECSNavigator(ecs_client_with_services)
    services = navigator.get_services("production")

    expected = ["web-api", "worker-service", "database-proxy"]
    assert sorted(services) == sorted(expected)


def test_get_services_from_empty_cluster(ecs_client_with_clusters):
    navigator = ECSNavigator(ecs_client_with_clusters)
    services = navigator.get_services("production")

    assert services == []


@patch("lazy_ecs.interactive.questionary.select")
def test_select_service_interactive(mock_select, ecs_client_with_services):
    mock_select.return_value.ask.return_value = "web-api"

    navigator = ECSNavigator(ecs_client_with_services)
    selected = navigator.select_service("production")

    assert selected == "web-api"
    mock_select.assert_called_once()


@patch("lazy_ecs.interactive.questionary.select")
def test_select_service_interactive_no_services(mock_select, ecs_client_with_clusters):
    navigator = ECSNavigator(ecs_client_with_clusters)
    selected = navigator.select_service("production")

    assert selected == ""
    mock_select.assert_not_called()
