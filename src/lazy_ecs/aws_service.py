"""AWS ECS service layer - handles all AWS API interactions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import boto3

from .core.types import LogConfig, ServiceInfo, TaskDetails, TaskInfo
from .features.cluster.cluster import ClusterService
from .features.service.actions import ServiceActions
from .features.service.service import ServiceService
from .features.task.task import TaskService

if TYPE_CHECKING:
    from mypy_boto3_ecs.client import ECSClient
    from mypy_boto3_logs.client import CloudWatchLogsClient
    from mypy_boto3_logs.type_defs import OutputLogEventTypeDef


class ECSService:
    """Service for interacting with AWS ECS."""

    def __init__(self, ecs_client: ECSClient) -> None:
        self.ecs_client = ecs_client
        # Initialize feature services
        self._cluster = ClusterService(ecs_client)
        self._service = ServiceService(ecs_client)
        self._service_actions = ServiceActions(ecs_client)
        self._task = TaskService(ecs_client)

    def get_cluster_names(self) -> list[str]:
        """Get list of ECS cluster names from AWS."""
        return self._cluster.get_cluster_names()

    def get_services(self, cluster_name: str) -> list[str]:
        """Get list of service names in a cluster."""
        return self._service.get_services(cluster_name)

    def get_service_info(self, cluster_name: str) -> list[ServiceInfo]:
        """Get detailed service information with status."""
        return self._service.get_service_info(cluster_name)

    def get_tasks(self, cluster_name: str, service_name: str) -> list[str]:
        """Get list of task ARNs for a service."""
        return self._task.get_tasks(cluster_name, service_name)

    def get_task_info(self, cluster_name: str, service_name: str) -> list[TaskInfo]:
        """Get detailed task information with human-readable names."""
        desired_task_def_arn = self._service.get_desired_task_definition_arn(cluster_name, service_name)
        return self._task.get_task_info(cluster_name, service_name, desired_task_def_arn)

    def get_task_details(self, cluster_name: str, service_name: str, task_arn: str) -> TaskDetails | None:
        """Get comprehensive task details."""
        desired_task_def_arn = self._service.get_desired_task_definition_arn(cluster_name, service_name)
        return self._task.get_task_details(cluster_name, task_arn, desired_task_def_arn)

    def get_log_config(self, cluster_name: str, task_arn: str, container_name: str) -> LogConfig | None:
        """Get log configuration for a container."""
        result = self._task.get_task_and_definition(cluster_name, task_arn)
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
        result = self._task.get_task_and_definition(cluster_name, task_arn)
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
        result = self._task.get_task_and_definition(cluster_name, task_arn)
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
        result = self._task.get_task_and_definition(cluster_name, task_arn)
        if not result:
            return None

        _task, task_definition = result

        for container_def in task_definition["containerDefinitions"]:
            if container_def["name"] == container_name:
                port_mappings = container_def.get("portMappings", [])
                return [dict(mapping) for mapping in port_mappings]

        return None

    def get_container_volume_mounts(
        self, cluster_name: str, task_arn: str, container_name: str
    ) -> list[dict[str, Any]] | None:
        """Get volume mounts for a specific container in a task."""
        result = self._task.get_task_and_definition(cluster_name, task_arn)
        if not result:
            return None

        _task, task_definition = result

        # Get the container definition
        container_def = None
        for cont_def in task_definition["containerDefinitions"]:
            if cont_def["name"] == container_name:
                container_def = cont_def
                break

        if not container_def:
            return None

        mount_points = container_def.get("mountPoints", [])
        if not mount_points:
            return []

        # Build volume lookup map from task definition volumes
        volumes_map = {}
        for volume in task_definition.get("volumes", []):
            volume_name = volume["name"]
            host_config = volume.get("host", {})
            host_path = host_config.get("sourcePath") if host_config else None
            volumes_map[volume_name] = host_path

        # Build volume mounts with resolved host paths
        volume_mounts = []
        for mount_point in mount_points:
            source_volume = mount_point["sourceVolume"]
            host_path = volumes_map.get(source_volume)

            volume_mount = {
                "source_volume": source_volume,
                "container_path": mount_point["containerPath"],
                "read_only": mount_point.get("readOnly", False),
                "host_path": host_path,
            }
            volume_mounts.append(volume_mount)

        return volume_mounts

    def force_new_deployment(self, cluster_name: str, service_name: str) -> bool:
        """Force a new deployment for a service."""
        return self._service_actions.force_new_deployment(cluster_name, service_name)
