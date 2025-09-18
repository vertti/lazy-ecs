"""Context objects for passing rich data between components."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypy_boto3_ecs.type_defs import ContainerDefinitionOutputTypeDef, TaskDefinitionTypeDef


@dataclass
class ContainerContext:
    """Rich context object for container operations."""

    cluster_name: str
    service_name: str
    task_arn: str
    container_name: str
    task_definition: TaskDefinitionTypeDef
    container_definition: ContainerDefinitionOutputTypeDef

    @property
    def task_id(self) -> str:
        """Extract task ID from task ARN."""
        return self.task_arn.split("/")[-1]

    @property
    def short_task_id(self) -> str:
        """Extract short task ID for display."""
        return self.task_id[:8]
