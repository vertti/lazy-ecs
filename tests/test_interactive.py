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
        client.create_service(cluster="production", serviceName="web-api", taskDefinition="web-api-task")
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


def test_get_service_choices_with_state_info(ecs_client_with_services):
    navigator = ECSNavigator(ecs_client_with_services)
    service_choices = navigator.get_service_choices("production")

    assert len(service_choices) == 3
    for choice in service_choices:
        assert "name" in choice
        assert "value" in choice
        assert "status" in choice
        assert "running_count" in choice
        assert "desired_count" in choice
        assert choice["value"] in ["web-api", "worker-service", "database-proxy"]
        # All services should show as HEALTHY since they have desiredCount=0 by default in moto
        assert "✅" in choice["name"] or "⚠️" in choice["name"]


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
    # Verify that the choices passed to questionary are dictionaries with enhanced info
    call_kwargs = mock_select.call_args[1]
    assert "choices" in call_kwargs
    choices = call_kwargs["choices"]
    assert len(choices) == 3
    for choice in choices:
        assert isinstance(choice, dict)
        assert "name" in choice
        assert "value" in choice


@patch("lazy_ecs.interactive.questionary.select")
def test_select_service_interactive_no_services(mock_select, ecs_client_with_clusters):
    navigator = ECSNavigator(ecs_client_with_clusters)
    selected = navigator.select_service("production")

    assert selected == ""
    mock_select.assert_not_called()


def test_get_service_choices_empty_cluster(ecs_client_with_clusters):
    navigator = ECSNavigator(ecs_client_with_clusters)
    service_choices = navigator.get_service_choices("production")

    assert service_choices == []


@pytest.fixture
def ecs_client_with_tasks():
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")

        client.create_cluster(clusterName="production")

        client.register_task_definition(
            family="web-api-task",
            containerDefinitions=[{"name": "web", "image": "nginx", "memory": 256}],
        )

        client.create_service(
            cluster="production",
            serviceName="web-api",
            taskDefinition="web-api-task",
            desiredCount=3,
        )

        # Start some tasks for the service
        client.run_task(
            cluster="production",
            taskDefinition="web-api-task",
            count=3,
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": ["subnet-12345"],
                    "assignPublicIp": "ENABLED",
                }
            },
        )

        yield client


def test_get_tasks_from_service(ecs_client_with_tasks):
    navigator = ECSNavigator(ecs_client_with_tasks)
    tasks = navigator.get_tasks("production", "web-api")

    assert len(tasks) == 3
    for task_arn in tasks:
        assert isinstance(task_arn, str)
        assert task_arn.startswith("arn:aws:ecs:")


def test_get_tasks_from_service_no_tasks(ecs_client_with_services):
    navigator = ECSNavigator(ecs_client_with_services)
    tasks = navigator.get_tasks("production", "web-api")

    assert tasks == []


@patch("lazy_ecs.interactive.questionary.select")
def test_select_task_interactive_multiple_tasks(mock_select, ecs_client_with_tasks):
    mock_select.return_value.ask.return_value = "task-123"

    navigator = ECSNavigator(ecs_client_with_tasks)
    selected = navigator.select_task("production", "web-api")

    assert selected == "task-123"
    mock_select.assert_called_once()


def test_select_task_auto_select_single_task():
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")

        client.create_cluster(clusterName="production")
        client.register_task_definition(
            family="web-api-task",
            containerDefinitions=[{"name": "web", "image": "nginx", "memory": 256}],
        )
        client.create_service(cluster="production", serviceName="web-api", taskDefinition="web-api-task")

        # Start only one task
        response = client.run_task(
            cluster="production",
            taskDefinition="web-api-task",
            count=1,
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": ["subnet-12345"],
                    "assignPublicIp": "ENABLED",
                }
            },
        )

        navigator = ECSNavigator(client)
        selected = navigator.select_task("production", "web-api")

        # Should auto-select the single task and return the full ARN
        expected_task_arn = response["tasks"][0]["taskArn"]
        assert selected == expected_task_arn


@patch("lazy_ecs.interactive.questionary.select")
def test_select_task_no_tasks(mock_select, ecs_client_with_services):
    navigator = ECSNavigator(ecs_client_with_services)
    selected = navigator.select_task("production", "web-api")

    assert selected == ""
    mock_select.assert_not_called()


def test_get_readable_task_names(ecs_client_with_tasks):
    navigator = ECSNavigator(ecs_client_with_tasks)
    task_choices = navigator.get_readable_task_choices("production", "web-api")

    assert len(task_choices) == 3
    for choice in task_choices:
        # Each choice should be a TaskChoice TypedDict
        assert "name" in choice
        assert "value" in choice
        assert "task_def_arn" in choice
        assert "is_desired" in choice
        assert "revision" in choice
        assert "images" in choice
        # Should contain version indicator (either ✅ or 🔴)
        assert "✅" in choice["name"] or "🔴" in choice["name"]
        # Should contain revision number
        assert f"v{choice['revision']}" in choice["name"]
