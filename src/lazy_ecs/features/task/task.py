"""Task operations for ECS."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...core.base import BaseAWSService
from ...core.types import TaskDetails, TaskInfo

if TYPE_CHECKING:
    from mypy_boto3_ecs.client import ECSClient
    from mypy_boto3_ecs.type_defs import TaskDefinitionTypeDef, TaskTypeDef


class TaskService(BaseAWSService):
    """Service for ECS task operations."""

    def __init__(self, ecs_client: ECSClient) -> None:
        super().__init__(ecs_client)

    def get_tasks(self, cluster_name: str, service_name: str) -> list[str]:
        """Get list of task ARNs for a service."""
        response = self.ecs_client.list_tasks(cluster=cluster_name, serviceName=service_name)
        return response.get("taskArns", [])

    def get_task_info(self, cluster_name: str, service_name: str, desired_task_def_arn: str | None) -> list[TaskInfo]:
        """Get detailed task information with human-readable names."""
        task_arns = self.get_tasks(cluster_name, service_name)
        if not task_arns:
            return []

        response = self.ecs_client.describe_tasks(cluster=cluster_name, tasks=task_arns)
        tasks = response.get("tasks", [])
        return [_create_task_info(task, desired_task_def_arn) for task in tasks]

    def get_task_details(
        self, cluster_name: str, task_arn: str, desired_task_def_arn: str | None
    ) -> TaskDetails | None:
        """Get comprehensive task details."""
        result = self.get_task_and_definition(cluster_name, task_arn)
        if not result:
            return None

        task, task_definition = result
        is_desired_version = task["taskDefinitionArn"] == desired_task_def_arn
        return _build_task_details(task, task_definition, is_desired_version)

    def get_task_and_definition(
        self, cluster_name: str, task_arn: str
    ) -> tuple[TaskTypeDef, TaskDefinitionTypeDef] | None:
        """Get task and its task definition from ECS."""
        task_response = self.ecs_client.describe_tasks(cluster=cluster_name, tasks=[task_arn])
        tasks = task_response.get("tasks", [])
        if not tasks:
            return None

        task = tasks[0]
        task_def_arn = task["taskDefinitionArn"]
        task_def_response = self.ecs_client.describe_task_definition(taskDefinition=task_def_arn)
        task_definition = task_def_response["taskDefinition"]

        return task, task_definition


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
