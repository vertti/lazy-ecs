"""Tests for AWS service layer."""

import boto3
import pytest
from moto import mock_aws

from lazy_ecs.aws_service import ECSService


@pytest.fixture
def ecs_client_with_clusters():
    """Create a mocked ECS client with test clusters."""
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")

        client.create_cluster(clusterName="production")
        client.create_cluster(clusterName="staging")
        client.create_cluster(clusterName="dev")

        yield client


@pytest.fixture
def ecs_client_with_services():
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")

        client.create_cluster(clusterName="production")

        client.register_task_definition(
            family="web-api-task",
            containerDefinitions=[{"name": "web", "image": "nginx", "memory": 256}],
        )
        client.register_task_definition(
            family="worker-task",
            containerDefinitions=[{"name": "worker", "image": "worker", "memory": 256}],
        )

        client.create_service(cluster="production", serviceName="web-api", taskDefinition="web-api-task")
        client.create_service(cluster="production", serviceName="worker-service", taskDefinition="worker-task")

        yield client


@pytest.fixture
def ecs_client_with_tasks():
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")

        client.create_cluster(clusterName="production")

        client.register_task_definition(
            family="web-api-task",
            containerDefinitions=[
                {
                    "name": "web",
                    "image": "nginx",
                    "memory": 256,
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {"awslogs-group": "/ecs/production/web", "awslogs-stream-prefix": "ecs"},
                    },
                }
            ],
        )

        client.create_service(
            cluster="production",
            serviceName="web-api",
            taskDefinition="web-api-task",
            desiredCount=3,
        )

        client.run_task(
            cluster="production",
            taskDefinition="web-api-task",
            count=2,
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": ["subnet-12345"],
                    "assignPublicIp": "ENABLED",
                }
            },
        )

        yield client


@pytest.fixture
def ecs_client_with_env_vars():
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")

        client.create_cluster(clusterName="production")

        client.register_task_definition(
            family="app-with-env",
            containerDefinitions=[
                {
                    "name": "app",
                    "image": "myapp:latest",
                    "memory": 512,
                    "environment": [
                        {"name": "ENV", "value": "production"},
                        {"name": "DEBUG", "value": "false"},
                        {"name": "DATABASE_URL", "value": "postgres://prod-db:5432/myapp"},
                        {"name": "API_KEY", "value": "secret-key-123"},
                    ],
                },
                {
                    "name": "sidecar",
                    "image": "nginx:latest",
                    "memory": 256,
                    "environment": [
                        {"name": "NGINX_PORT", "value": "8080"},
                    ],
                },
            ],
        )

        client.create_service(
            cluster="production",
            serviceName="app-service",
            taskDefinition="app-with-env",
            desiredCount=1,
        )

        client.run_task(
            cluster="production",
            taskDefinition="app-with-env",
            launchType="FARGATE",
        )

        yield client


@pytest.fixture
def ecs_client_with_secrets():
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")

        client.create_cluster(clusterName="production")

        client.register_task_definition(
            family="app-with-secrets",
            containerDefinitions=[
                {
                    "name": "app",
                    "image": "myapp:latest",
                    "memory": 512,
                    "environment": [
                        {"name": "ENV", "value": "production"},
                    ],
                    "secrets": [
                        {
                            "name": "DATABASE_PASSWORD",
                            "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:db-password-AbCdEf",
                        },
                        {
                            "name": "API_KEY",
                            "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:api-key-XyZ123",
                        },
                    ],
                },
                {
                    "name": "sidecar",
                    "image": "nginx:latest",
                    "memory": 256,
                    "secrets": [
                        {
                            "name": "SSL_CERT",
                            "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:ssl-cert-MnOpQr",
                        }
                    ],
                },
            ],
        )

        client.create_service(
            cluster="production",
            serviceName="app-service",
            taskDefinition="app-with-secrets",
            desiredCount=1,
        )

        client.run_task(
            cluster="production",
            taskDefinition="app-with-secrets",
            launchType="FARGATE",
        )

        yield client


def test_get_cluster_names(ecs_client_with_clusters) -> None:
    service = ECSService(ecs_client_with_clusters)
    clusters = service.get_cluster_names()

    expected = ["production", "staging", "dev"]
    assert sorted(clusters) == sorted(expected)


def test_get_cluster_names_empty():
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")
        service = ECSService(client)
        clusters = service.get_cluster_names()
        assert clusters == []


def test_get_cluster_names_pagination():
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")

        for i in range(150):
            client.create_cluster(clusterName=f"cluster-{i:03d}")

        service = ECSService(client)
        clusters = service.get_cluster_names()

        assert len(clusters) == 150
        assert "cluster-000" in clusters
        assert "cluster-149" in clusters


def test_get_services(ecs_client_with_services) -> None:
    service = ECSService(ecs_client_with_services)
    services = service.get_services("production")

    expected = ["web-api", "worker-service"]
    assert sorted(services) == sorted(expected)


def test_get_services_pagination():
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")
        client.create_cluster(clusterName="production")

        client.register_task_definition(
            family="app-task",
            containerDefinitions=[{"name": "app", "image": "nginx", "memory": 256}],
        )

        for i in range(200):
            client.create_service(
                cluster="production", serviceName=f"service-{i:03d}", taskDefinition="app-task", desiredCount=1
            )

        service = ECSService(client)
        services = service.get_services("production")

        assert len(services) == 200
        assert "service-000" in services
        assert "service-199" in services


def test_get_service_info(ecs_client_with_services) -> None:
    service = ECSService(ecs_client_with_services)
    service_info = service.get_service_info("production")

    assert len(service_info) == 2
    for info in service_info:
        assert "name" in info
        assert "status" in info
        assert "running_count" in info
        assert "desired_count" in info
        assert "pending_count" in info


def test_get_tasks(ecs_client_with_tasks) -> None:
    service = ECSService(ecs_client_with_tasks)
    tasks = service.get_tasks("production", "web-api")

    assert len(tasks) == 2
    for task_arn in tasks:
        assert isinstance(task_arn, str)
        assert task_arn.startswith("arn:aws:ecs:")


def test_get_tasks_pagination(mock_paginated_client) -> None:
    task_arns = [f"arn:aws:ecs:us-east-1:123456789012:task/production/task-{i}" for i in range(200)]
    pages = [{"taskArns": task_arns[i : i + 100]} for i in range(0, 200, 100)]
    mock_client = mock_paginated_client(pages)

    service = ECSService(mock_client)
    tasks = service.get_tasks("production", "web-api")

    assert len(tasks) == 200
    for task_arn in tasks:
        assert isinstance(task_arn, str)
        assert task_arn.startswith("arn:aws:ecs:")

    mock_client.get_paginator.assert_called_once_with("list_tasks")


def test_get_task_info(ecs_client_with_tasks) -> None:
    service = ECSService(ecs_client_with_tasks)
    task_info = service.get_task_info("production", "web-api")

    assert len(task_info) == 2
    for info in task_info:
        assert "name" in info
        assert "value" in info
        assert "task_def_arn" in info
        assert "is_desired" in info
        assert "revision" in info
        assert "images" in info


def test_get_task_details(ecs_client_with_tasks) -> None:
    service = ECSService(ecs_client_with_tasks)
    tasks = service.get_tasks("production", "web-api")

    task_details = service.get_task_details("production", "web-api", tasks[0])

    assert task_details is not None
    assert "task_arn" in task_details
    assert "task_definition_name" in task_details
    assert "task_definition_revision" in task_details
    assert "is_desired_version" in task_details
    assert "task_status" in task_details
    assert "containers" in task_details

    container = task_details["containers"][0]
    assert container["name"] == "web"
    assert container["image"] == "nginx"


def test_get_log_config(ecs_client_with_tasks) -> None:
    service = ECSService(ecs_client_with_tasks)
    tasks = service.get_tasks("production", "web-api")

    log_config = service.get_log_config("production", tasks[0], "web")

    assert log_config is not None
    assert log_config["log_group"] == "/ecs/production/web"
    assert log_config["log_stream"].startswith("ecs/web/")


def test_get_log_config_no_config():
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")
        client.create_cluster(clusterName="production")

        client.register_task_definition(
            family="web-api-task",
            containerDefinitions=[{"name": "web", "image": "nginx", "memory": 256}],  # No log config
        )

        client.run_task(
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

        # List tasks directly since we didn't create a service
        response = client.list_tasks(cluster="production")
        tasks = response.get("taskArns", [])

        service = ECSService(client)
        log_config = service.get_log_config("production", tasks[0], "web")
        assert log_config is None


def test_get_container_environment_variables(ecs_client_with_env_vars) -> None:
    service = ECSService(ecs_client_with_env_vars)
    tasks = service.get_tasks("production", "app-service")

    env_vars = service.get_container_environment_variables("production", tasks[0], "app")

    assert env_vars is not None
    assert len(env_vars) == 4

    expected_vars = {
        "ENV": "production",
        "DEBUG": "false",
        "DATABASE_URL": "postgres://prod-db:5432/myapp",
        "API_KEY": "secret-key-123",
    }

    assert env_vars == expected_vars


def test_get_container_environment_variables_sidecar(ecs_client_with_env_vars) -> None:
    service = ECSService(ecs_client_with_env_vars)
    tasks = service.get_tasks("production", "app-service")

    env_vars = service.get_container_environment_variables("production", tasks[0], "sidecar")

    assert env_vars is not None
    assert len(env_vars) == 1
    assert env_vars["NGINX_PORT"] == "8080"


def test_get_container_environment_variables_no_container() -> None:
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")
        client.create_cluster(clusterName="production")

        client.register_task_definition(
            family="simple-task",
            containerDefinitions=[{"name": "web", "image": "nginx", "memory": 256}],
        )

        client.run_task(cluster="production", taskDefinition="simple-task", launchType="FARGATE")

        response = client.list_tasks(cluster="production")
        tasks = response.get("taskArns", [])

        service = ECSService(client)
        env_vars = service.get_container_environment_variables("production", tasks[0], "nonexistent")
        assert env_vars is None


def test_get_container_environment_variables_no_env_vars() -> None:
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")
        client.create_cluster(clusterName="production")

        client.register_task_definition(
            family="simple-task",
            containerDefinitions=[{"name": "web", "image": "nginx", "memory": 256}],
        )

        client.run_task(cluster="production", taskDefinition="simple-task", launchType="FARGATE")

        response = client.list_tasks(cluster="production")
        tasks = response.get("taskArns", [])

        service = ECSService(client)
        env_vars = service.get_container_environment_variables("production", tasks[0], "web")
        assert env_vars == {}


@pytest.fixture
def ecs_client_with_volume_mounts():
    """Create a mocked ECS client with tasks containing volume mounts."""
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")
        client.create_cluster(clusterName="production")

        client.register_task_definition(
            family="app-with-volumes-task",
            volumes=[
                {"name": "data-volume", "host": {"sourcePath": "/opt/data"}},
                {"name": "logs-volume", "host": {"sourcePath": "/var/log/app"}},
                {"name": "config-volume"},  # Empty volume
            ],
            containerDefinitions=[
                {
                    "name": "app",
                    "image": "myapp:latest",
                    "memory": 512,
                    "mountPoints": [
                        {"sourceVolume": "data-volume", "containerPath": "/app/data", "readOnly": False},
                        {"sourceVolume": "logs-volume", "containerPath": "/app/logs", "readOnly": False},
                        {"sourceVolume": "config-volume", "containerPath": "/app/config", "readOnly": True},
                    ],
                },
                {
                    "name": "sidecar",
                    "image": "sidecar:latest",
                    "memory": 256,
                    "mountPoints": [
                        {"sourceVolume": "logs-volume", "containerPath": "/shared/logs", "readOnly": True},
                    ],
                },
                {
                    "name": "no-mounts",
                    "image": "simple:latest",
                    "memory": 128,
                    "mountPoints": [],
                },
            ],
        )

        client.create_service(cluster="production", serviceName="app-service", taskDefinition="app-with-volumes-task")
        client.run_task(cluster="production", taskDefinition="app-with-volumes-task", launchType="FARGATE")

        yield client


def test_get_container_volume_mounts(ecs_client_with_volume_mounts) -> None:
    service = ECSService(ecs_client_with_volume_mounts)
    tasks = service.get_tasks("production", "app-service")

    # Test container with multiple mounts
    volume_mounts = service.get_container_volume_mounts("production", tasks[0], "app")
    assert volume_mounts is not None
    assert len(volume_mounts) == 3

    # Check data volume mount
    data_mount = next((mount for mount in volume_mounts if mount["source_volume"] == "data-volume"), None)
    assert data_mount is not None
    assert data_mount["container_path"] == "/app/data"
    assert data_mount["read_only"] is False
    assert data_mount["host_path"] == "/opt/data"

    # Check logs volume mount
    logs_mount = next((mount for mount in volume_mounts if mount["source_volume"] == "logs-volume"), None)
    assert logs_mount is not None
    assert logs_mount["container_path"] == "/app/logs"
    assert logs_mount["read_only"] is False
    assert logs_mount["host_path"] == "/var/log/app"

    # Check config volume (empty volume)
    config_mount = next((mount for mount in volume_mounts if mount["source_volume"] == "config-volume"), None)
    assert config_mount is not None
    assert config_mount["container_path"] == "/app/config"
    assert config_mount["read_only"] is True
    assert config_mount["host_path"] is None


def test_get_container_volume_mounts_sidecar(ecs_client_with_volume_mounts) -> None:
    service = ECSService(ecs_client_with_volume_mounts)
    tasks = service.get_tasks("production", "app-service")

    # Test sidecar with single mount
    volume_mounts = service.get_container_volume_mounts("production", tasks[0], "sidecar")
    assert volume_mounts is not None
    assert len(volume_mounts) == 1

    logs_mount = volume_mounts[0]
    assert logs_mount["source_volume"] == "logs-volume"
    assert logs_mount["container_path"] == "/shared/logs"
    assert logs_mount["read_only"] is True
    assert logs_mount["host_path"] == "/var/log/app"


def test_get_container_volume_mounts_no_mounts(ecs_client_with_volume_mounts) -> None:
    service = ECSService(ecs_client_with_volume_mounts)
    tasks = service.get_tasks("production", "app-service")

    # Test container with no mounts
    volume_mounts = service.get_container_volume_mounts("production", tasks[0], "no-mounts")
    assert volume_mounts == []


def test_get_container_volume_mounts_no_container(ecs_client_with_volume_mounts) -> None:
    service = ECSService(ecs_client_with_volume_mounts)
    tasks = service.get_tasks("production", "app-service")

    # Test nonexistent container
    volume_mounts = service.get_container_volume_mounts("production", tasks[0], "nonexistent")
    assert volume_mounts is None


def test_get_container_secrets(ecs_client_with_secrets) -> None:
    service = ECSService(ecs_client_with_secrets)
    tasks = service.get_tasks("production", "app-service")

    secrets = service.get_container_secrets("production", tasks[0], "app")

    assert secrets is not None
    assert len(secrets) == 2

    expected_secrets = {
        "DATABASE_PASSWORD": "arn:aws:secretsmanager:us-east-1:123456789012:secret:db-password-AbCdEf",
        "API_KEY": "arn:aws:secretsmanager:us-east-1:123456789012:secret:api-key-XyZ123",
    }

    assert secrets == expected_secrets


def test_get_container_secrets_sidecar(ecs_client_with_secrets) -> None:
    service = ECSService(ecs_client_with_secrets)
    tasks = service.get_tasks("production", "app-service")

    secrets = service.get_container_secrets("production", tasks[0], "sidecar")

    assert secrets is not None
    assert len(secrets) == 1
    assert secrets["SSL_CERT"] == "arn:aws:secretsmanager:us-east-1:123456789012:secret:ssl-cert-MnOpQr"


def test_get_container_secrets_no_container() -> None:
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")
        client.create_cluster(clusterName="production")

        client.register_task_definition(
            family="simple-task",
            containerDefinitions=[{"name": "web", "image": "nginx", "memory": 256}],
        )

        client.run_task(cluster="production", taskDefinition="simple-task", launchType="FARGATE")

        response = client.list_tasks(cluster="production")
        tasks = response.get("taskArns", [])

        service = ECSService(client)
        secrets = service.get_container_secrets("production", tasks[0], "nonexistent")
        assert secrets is None


def test_get_container_secrets_no_secrets() -> None:
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")
        client.create_cluster(clusterName="production")

        client.register_task_definition(
            family="simple-task",
            containerDefinitions=[{"name": "web", "image": "nginx", "memory": 256}],
        )

        client.run_task(cluster="production", taskDefinition="simple-task", launchType="FARGATE")

        response = client.list_tasks(cluster="production")
        tasks = response.get("taskArns", [])

        service = ECSService(client)
        secrets = service.get_container_secrets("production", tasks[0], "web")
        assert secrets == {}


@mock_aws
def test_get_container_port_mappings_success() -> None:
    client = boto3.client("ecs", region_name="us-east-1")
    client.create_cluster(clusterName="production")

    client.register_task_definition(
        family="web-task",
        containerDefinitions=[
            {
                "name": "web",
                "image": "nginx",
                "memory": 256,
                "portMappings": [
                    {"containerPort": 80, "hostPort": 8080, "protocol": "tcp"},
                    {"containerPort": 443, "hostPort": 0, "protocol": "tcp"},
                ],
            }
        ],
    )

    client.run_task(cluster="production", taskDefinition="web-task", launchType="FARGATE")
    response = client.list_tasks(cluster="production")
    tasks = response.get("taskArns", [])

    service = ECSService(client)
    port_mappings = service.get_container_port_mappings("production", tasks[0], "web")

    assert port_mappings is not None
    assert len(port_mappings) == 2
    assert port_mappings[0]["containerPort"] == 80
    assert port_mappings[0]["hostPort"] == 8080
    assert port_mappings[0]["protocol"] == "tcp"
    assert port_mappings[1]["containerPort"] == 443
    assert port_mappings[1]["hostPort"] == 0


@mock_aws
def test_get_container_port_mappings_no_mappings() -> None:
    client = boto3.client("ecs", region_name="us-east-1")
    client.create_cluster(clusterName="production")

    client.register_task_definition(
        family="simple-task",
        containerDefinitions=[{"name": "web", "image": "nginx", "memory": 256}],
    )

    client.run_task(cluster="production", taskDefinition="simple-task", launchType="FARGATE")
    response = client.list_tasks(cluster="production")
    tasks = response.get("taskArns", [])

    service = ECSService(client)
    port_mappings = service.get_container_port_mappings("production", tasks[0], "web")

    assert port_mappings == []


@mock_aws
def test_get_container_port_mappings_container_not_found() -> None:
    client = boto3.client("ecs", region_name="us-east-1")
    client.create_cluster(clusterName="production")

    client.register_task_definition(
        family="simple-task",
        containerDefinitions=[{"name": "web", "image": "nginx", "memory": 256}],
    )

    client.run_task(cluster="production", taskDefinition="simple-task", launchType="FARGATE")
    response = client.list_tasks(cluster="production")
    tasks = response.get("taskArns", [])

    service = ECSService(client)
    port_mappings = service.get_container_port_mappings("production", tasks[0], "nonexistent")

    assert port_mappings is None


@mock_aws
def test_force_new_deployment_success() -> None:
    client = boto3.client("ecs", region_name="us-east-1")
    client.create_cluster(clusterName="production")

    client.register_task_definition(
        family="web-task",
        containerDefinitions=[{"name": "web", "image": "nginx", "memory": 256}],
    )

    client.create_service(
        cluster="production",
        serviceName="web-service",
        taskDefinition="web-task",
        desiredCount=1,
    )

    service = ECSService(client)
    result = service.force_new_deployment("production", "web-service")

    assert result is True


@mock_aws
def test_force_new_deployment_service_not_found() -> None:
    client = boto3.client("ecs", region_name="us-east-1")
    client.create_cluster(clusterName="production")

    service = ECSService(client)
    result = service.force_new_deployment("production", "nonexistent-service")

    assert result is False


@pytest.fixture
def ecs_client_with_service_events():
    """Create a mocked ECS client with service events."""
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")
        client.create_cluster(clusterName="production")

        client.register_task_definition(
            family="web-task",
            containerDefinitions=[{"name": "web", "image": "nginx", "memory": 256}],
        )

        client.create_service(
            cluster="production",
            serviceName="web-service",
            taskDefinition="web-task",
            desiredCount=2,
        )

        yield client


def test_get_service_events_empty_service():
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")
        client.create_cluster(clusterName="production")

        service = ECSService(client)
        events = service.get_service_events("production", "nonexistent-service")
        assert events == []


def test_get_service_events_no_events(ecs_client_with_service_events):
    service = ECSService(ecs_client_with_service_events)
    events = service.get_service_events("production", "web-service")

    # Moto doesn't create events by default, so we expect an empty list
    assert isinstance(events, list)
