"""AWS ECS service layer - handles all AWS API interactions."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, TypedDict, cast

import boto3

if TYPE_CHECKING:
    from mypy_boto3_ecs.client import ECSClient
    from mypy_boto3_ecs.type_defs import ServiceTypeDef, TaskDefinitionTypeDef, TaskTypeDef
    from mypy_boto3_logs.client import CloudWatchLogsClient
    from mypy_boto3_logs.type_defs import OutputLogEventTypeDef


class ServiceInfo(TypedDict):
    name: str
    status: str
    running_count: int
    desired_count: int
    pending_count: int


class TaskInfo(TypedDict):
    name: str
    value: str
    task_def_arn: str
    is_desired: bool
    revision: str
    images: list[str]
    created_at: datetime | None


class TaskDetails(TypedDict):
    task_arn: str
    task_definition_name: str
    task_definition_revision: str
    is_desired_version: bool
    task_status: str
    containers: list[dict[str, Any]]
    created_at: datetime | None
    started_at: datetime | None


class LogConfig(TypedDict):
    log_group: str
    log_stream: str


class ECSService:
    """Service for interacting with AWS ECS."""

    def __init__(self, ecs_client: ECSClient) -> None:
        self.ecs_client = ecs_client

    def get_cluster_names(self) -> list[str]:
        """Get list of ECS cluster names from AWS."""
        response = self.ecs_client.list_clusters()
        cluster_arns = response.get("clusterArns", [])
        return [_extract_name_from_arn(arn) for arn in cluster_arns]

    def get_services(self, cluster_name: str) -> list[str]:
        """Get list of service names in a cluster."""
        response = self.ecs_client.list_services(cluster=cluster_name)
        service_arns = response.get("serviceArns", [])
        return [_extract_name_from_arn(arn) for arn in service_arns]

    def get_service_info(self, cluster_name: str) -> list[ServiceInfo]:
        """Get detailed service information with status."""
        service_names = self.get_services(cluster_name)
        if not service_names:
            return []

        response = self.ecs_client.describe_services(cluster=cluster_name, services=service_names)
        services = response.get("services", [])
        return [_create_service_info(service) for service in services]

    def get_tasks(self, cluster_name: str, service_name: str) -> list[str]:
        """Get list of task ARNs for a service."""
        response = self.ecs_client.list_tasks(cluster=cluster_name, serviceName=service_name)
        return response.get("taskArns", [])

    def get_task_info(self, cluster_name: str, service_name: str) -> list[TaskInfo]:
        """Get detailed task information with human-readable names."""
        task_arns = self.get_tasks(cluster_name, service_name)
        if not task_arns:
            return []

        response = self.ecs_client.describe_tasks(cluster=cluster_name, tasks=task_arns)
        tasks = response.get("tasks", [])
        desired_task_def_arn = _get_desired_task_definition_arn(self.ecs_client, cluster_name, service_name)
        return [_create_task_info(task, desired_task_def_arn) for task in tasks]

    def get_task_details(self, cluster_name: str, service_name: str, task_arn: str) -> TaskDetails | None:
        """Get comprehensive task details."""
        result = _get_task_and_definition(self.ecs_client, cluster_name, task_arn)
        if not result:
            return None

        task, task_definition = result
        desired_task_def_arn = _get_desired_task_definition_arn(self.ecs_client, cluster_name, service_name)
        is_desired_version = task["taskDefinitionArn"] == desired_task_def_arn
        return _build_task_details(task, task_definition, is_desired_version)

    def get_log_config(self, cluster_name: str, task_arn: str, container_name: str) -> LogConfig | None:
        """Get log configuration for a container."""
        result = _get_task_and_definition(self.ecs_client, cluster_name, task_arn)
        if not result:
            return None

        _task, task_definition = result

        for container_def in task_definition["containerDefinitions"]:
            if container_def["name"] == container_name:
                log_config = container_def.get("logConfiguration", {})

                if log_config.get("logDriver") != "awslogs":
                    return None

                options = cast(dict[str, str], log_config.get("options", {}))
                log_group = options.get("awslogs-group")
                stream_prefix = options.get("awslogs-stream-prefix", "ecs")

                if not log_group:
                    return None

                task_id = task_arn.split("/")[-1]
                log_stream = f"{stream_prefix}/{container_name}/{task_id}"

                return {"log_group": log_group, "log_stream": log_stream}

        return None

    def get_container_logs(self, log_group: str, log_stream: str, lines: int = 50) -> list[OutputLogEventTypeDef]:
        """Get container logs from CloudWatch."""
        logs_client: CloudWatchLogsClient = boto3.client("logs")

        response = logs_client.get_log_events(
            logGroupName=log_group, logStreamName=log_stream, limit=lines, startFromHead=False
        )
        return response.get("events", [])

    def list_log_groups(self, cluster_name: str, container_name: str) -> list[str]:
        """List available log groups for debugging."""
        logs_client: CloudWatchLogsClient = boto3.client("logs")

        response = logs_client.describe_log_groups(limit=50)
        groups = response.get("logGroups", [])

        relevant_groups = []
        for group in groups[:10]:
            name = group["logGroupName"]
            if cluster_name.lower() in name.lower() or container_name.lower() in name.lower() or "ecs" in name.lower():
                relevant_groups.append(name)

        return relevant_groups

    def get_container_environment_variables(
        self, cluster_name: str, task_arn: str, container_name: str
    ) -> dict[str, str] | None:
        """Get environment variables for a specific container in a task."""
        result = _get_task_and_definition(self.ecs_client, cluster_name, task_arn)
        if not result:
            return None

        _task, task_definition = result

        for container_def in task_definition["containerDefinitions"]:
            if container_def["name"] == container_name:
                environment = container_def.get("environment", [])
                return {env_var["name"]: env_var["value"] for env_var in environment}

        return None

    def get_container_secrets(self, cluster_name: str, task_arn: str, container_name: str) -> dict[str, str] | None:
        """Get secrets configuration for a specific container in a task."""
        result = _get_task_and_definition(self.ecs_client, cluster_name, task_arn)
        if not result:
            return None

        _task, task_definition = result

        for container_def in task_definition["containerDefinitions"]:
            if container_def["name"] == container_name:
                secrets = container_def.get("secrets", [])
                return {secret["name"]: secret["valueFrom"] for secret in secrets}

        return None

    def get_container_port_mappings(
        self, cluster_name: str, task_arn: str, container_name: str
    ) -> list[dict[str, Any]] | None:
        """Get port mappings for a specific container in a task."""
        result = _get_task_and_definition(self.ecs_client, cluster_name, task_arn)
        if not result:
            return None

        _task, task_definition = result

        for container_def in task_definition["containerDefinitions"]:
            if container_def["name"] == container_name:
                port_mappings = container_def.get("portMappings", [])
                return [dict(mapping) for mapping in port_mappings]

        return None


def _extract_name_from_arn(arn: str) -> str:
    """Extract resource name from AWS ARN."""
    return arn.split("/")[-1]


def _get_task_and_definition(
    ecs_client: ECSClient, cluster_name: str, task_arn: str
) -> tuple[TaskTypeDef, TaskDefinitionTypeDef] | None:
    """Get task and its task definition from ECS."""
    task_response = ecs_client.describe_tasks(cluster=cluster_name, tasks=[task_arn])
    tasks = task_response.get("tasks", [])
    if not tasks:
        return None

    task = tasks[0]
    task_def_arn = task["taskDefinitionArn"]
    task_def_response = ecs_client.describe_task_definition(taskDefinition=task_def_arn)
    task_definition = task_def_response["taskDefinition"]

    return task, task_definition


def _create_service_info(service: ServiceTypeDef) -> ServiceInfo:
    """Create service info from AWS service description."""
    service_name = service["serviceName"]
    running_count = service.get("runningCount", 0)
    desired_count = service.get("desiredCount", 0)
    pending_count = service.get("pendingCount", 0)

    icon, status = _determine_service_status(running_count, desired_count, pending_count)

    display_name = f"{icon} {service_name} ({running_count}/{desired_count})"

    return {
        "name": display_name,
        "status": status,
        "running_count": running_count,
        "desired_count": desired_count,
        "pending_count": pending_count,
    }


def _determine_service_status(running_count: int, desired_count: int, pending_count: int) -> tuple[str, str]:
    """Determine service status icon and text."""
    if running_count == desired_count and pending_count == 0:
        return "✅", "HEALTHY"
    if running_count < desired_count:
        return "⚠️", "SCALING"
    if running_count > desired_count:
        return "🔴", "OVER_SCALED"
    return "🟡", "PENDING"


def _get_desired_task_definition_arn(ecs_client: ECSClient, cluster_name: str, service_name: str) -> str | None:
    """Get the desired task definition ARN for a service."""
    response = ecs_client.describe_services(cluster=cluster_name, services=[service_name])
    services = response.get("services", [])
    if services:
        return services[0].get("taskDefinition")
    return None


def _create_task_info(task: TaskTypeDef, desired_task_def_arn: str | None) -> TaskInfo:
    """Create task info from AWS task description."""
    task_arn = task["taskArn"]
    task_def_arn = task["taskDefinitionArn"]
    is_desired = task_def_arn == desired_task_def_arn

    task_id = task_arn.split("/")[-1][:8]
    task_def_family = task_def_arn.split("/")[-1].split(":")[0]
    revision = task_def_arn.split(":")[-1]

    created_at = task.get("createdAt")

    container_images = []
    for container in task.get("containers", []):
        if "image" in container:
            image = container["image"]
            if ":" in image:
                container_images.append(image.split(":")[-1])

    image_display = ", ".join(container_images) if container_images else "unknown"

    status_icon = "✅" if is_desired else "🔴"
    time_str = created_at.strftime("%H:%M:%S") if created_at else "unknown"

    display_name = f"{status_icon} v{revision} {task_def_family} ({task_id}) - {image_display} - {time_str}"

    return {
        "name": display_name,
        "value": task_arn,
        "task_def_arn": task_def_arn,
        "is_desired": is_desired,
        "revision": revision,
        "images": container_images,
        "created_at": created_at,
    }


def _build_task_details(
    task: TaskTypeDef, task_definition: TaskDefinitionTypeDef, is_desired_version: bool
) -> TaskDetails:
    """Build comprehensive task details dictionary."""
    task_arn = task["taskArn"]
    task_def_arn = task["taskDefinitionArn"]
    task_def_family = task_def_arn.split("/")[-1].split(":")[0]
    task_def_revision = task_def_arn.split(":")[-1]

    containers = []
    for container_def in task_definition["containerDefinitions"]:
        container_info = {
            "name": container_def["name"],
            "image": container_def["image"],
            "cpu": container_def.get("cpu"),
            "memory": container_def.get("memory"),
            "memoryReservation": container_def.get("memoryReservation"),
        }
        containers.append(container_info)

    return {
        "task_arn": task_arn,
        "task_definition_name": task_def_family,
        "task_definition_revision": task_def_revision,
        "is_desired_version": is_desired_version,
        "task_status": task.get("lastStatus", "UNKNOWN"),
        "containers": containers,
        "created_at": task.get("createdAt"),
        "started_at": task.get("startedAt"),
    }
