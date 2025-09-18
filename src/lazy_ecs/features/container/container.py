"""Container operations for ECS."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...core.base import BaseAWSService
from ...core.context import ContainerContext
from ...core.types import LogConfig

if TYPE_CHECKING:
    from mypy_boto3_ecs.client import ECSClient
    from mypy_boto3_ecs.type_defs import ContainerDefinitionOutputTypeDef, TaskDefinitionTypeDef

    from ..task.task import TaskService


class ContainerService(BaseAWSService):
    """Service for ECS container operations."""

    def __init__(self, ecs_client: ECSClient, task_service: TaskService) -> None:
        super().__init__(ecs_client)
        self.task_service = task_service

    def get_container_context(self, cluster_name: str, task_arn: str, container_name: str) -> ContainerContext | None:
        """Create a rich container context for operations."""
        result = self.task_service.get_task_and_definition(cluster_name, task_arn)
        if not result:
            return None

        _task, task_definition = result

        # Find the container definition
        for container_def in task_definition["containerDefinitions"]:
            if container_def["name"] == container_name:
                return ContainerContext(
                    cluster_name=cluster_name,
                    service_name="",  # We don't always have service name in this context
                    task_arn=task_arn,
                    container_name=container_name,
                    task_definition=task_definition,
                    container_definition=container_def,
                )

        return None

    def get_container_definition(
        self, task_definition: TaskDefinitionTypeDef, container_name: str
    ) -> ContainerDefinitionOutputTypeDef | None:
        """Get container definition from task definition."""
        for container_def in task_definition["containerDefinitions"]:
            if container_def["name"] == container_name:
                return container_def
        return None

    def get_log_config(self, cluster_name: str, task_arn: str, container_name: str) -> LogConfig | None:
        """Get log configuration for a container."""
        context = self.get_container_context(cluster_name, task_arn, container_name)
        if not context:
            return None

        log_config = context.container_definition.get("logConfiguration", {})

        if log_config.get("logDriver") != "awslogs":
            return None

        options = log_config.get("options") or {}
        log_group = options.get("awslogs-group") if options else None
        stream_prefix = options.get("awslogs-stream-prefix", "ecs") if options else "ecs"

        if not log_group:
            return None

        log_stream = f"{stream_prefix}/{container_name}/{context.task_id}"

        return {"log_group": log_group, "log_stream": log_stream}
