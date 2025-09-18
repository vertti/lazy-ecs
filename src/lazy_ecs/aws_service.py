"""AWS ECS service layer - handles all AWS API interactions."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from .core.types import LogConfig, ServiceInfo, TaskDetails, TaskInfo
from .features.cluster.cluster import ClusterService
from .features.container.container import ContainerService
from .features.service.actions import ServiceActions
from .features.service.service import ServiceService
from .features.task.task import TaskService

if TYPE_CHECKING:
    from mypy_boto3_ecs.client import ECSClient
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
        self._container = ContainerService(ecs_client, self._task)

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

    def _with_desired_task_definition(
        self, cluster_name: str, service_name: str, operation: Callable[[str | None], Any]
    ) -> Any:  # noqa: ANN401
        """Helper to reduce repetition in task operations that need desired task definition."""
        desired_task_def_arn = self._service.get_desired_task_definition_arn(cluster_name, service_name)
        return operation(desired_task_def_arn)

    def get_task_info(self, cluster_name: str, service_name: str) -> list[TaskInfo]:
        """Get detailed task information with human-readable names."""
        return self._with_desired_task_definition(
            cluster_name, service_name, lambda arn: self._task.get_task_info(cluster_name, service_name, arn)
        )

    def get_task_details(self, cluster_name: str, service_name: str, task_arn: str) -> TaskDetails | None:
        """Get comprehensive task details."""
        return self._with_desired_task_definition(
            cluster_name, service_name, lambda arn: self._task.get_task_details(cluster_name, task_arn, arn)
        )

    def get_log_config(self, cluster_name: str, task_arn: str, container_name: str) -> LogConfig | None:
        """Get log configuration for a container."""
        return self._container.get_log_config(cluster_name, task_arn, container_name)

    def get_container_logs(self, log_group: str, log_stream: str, lines: int = 50) -> list[OutputLogEventTypeDef]:
        """Get container logs from CloudWatch."""
        return self._container.get_container_logs(log_group, log_stream, lines)

    def list_log_groups(self, cluster_name: str, container_name: str) -> list[str]:
        """List available log groups for debugging."""
        return self._container.list_log_groups(cluster_name, container_name)

    def _with_container_context(
        self, cluster_name: str, task_arn: str, container_name: str, operation: Callable[[Any], Any]
    ) -> Any:  # noqa: ANN401
        """Helper to reduce repetition in container operations."""
        context = self._container.get_container_context(cluster_name, task_arn, container_name)
        if not context:
            return None
        return operation(context)

    def get_container_environment_variables(
        self, cluster_name: str, task_arn: str, container_name: str
    ) -> dict[str, str] | None:
        """Get environment variables for a specific container in a task."""
        return self._with_container_context(
            cluster_name, task_arn, container_name, self._container.get_environment_variables
        )

    def get_container_secrets(self, cluster_name: str, task_arn: str, container_name: str) -> dict[str, str] | None:
        """Get secrets configuration for a specific container in a task."""
        return self._with_container_context(cluster_name, task_arn, container_name, self._container.get_secrets)

    def get_container_port_mappings(
        self, cluster_name: str, task_arn: str, container_name: str
    ) -> list[dict[str, Any]] | None:
        """Get port mappings for a specific container in a task."""
        return self._with_container_context(cluster_name, task_arn, container_name, self._container.get_port_mappings)

    def get_container_volume_mounts(
        self, cluster_name: str, task_arn: str, container_name: str
    ) -> list[dict[str, Any]] | None:
        """Get volume mounts for a specific container in a task."""
        return self._with_container_context(cluster_name, task_arn, container_name, self._container.get_volume_mounts)

    def force_new_deployment(self, cluster_name: str, service_name: str) -> bool:
        """Force a new deployment for a service."""
        return self._service_actions.force_new_deployment(cluster_name, service_name)
