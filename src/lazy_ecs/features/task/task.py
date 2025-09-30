"""Task operations for ECS."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...core.base import BaseAWSService
from ...core.types import TaskDetails, TaskHistoryDetails, TaskInfo
from ...core.utils import paginate_aws_list

if TYPE_CHECKING:
    from mypy_boto3_ecs.client import ECSClient
    from mypy_boto3_ecs.type_defs import TaskDefinitionTypeDef, TaskTypeDef


class TaskService(BaseAWSService):
    """Service for ECS task operations."""

    def __init__(self, ecs_client: ECSClient) -> None:
        super().__init__(ecs_client)

    def get_tasks(self, cluster_name: str, service_name: str) -> list[str]:
        return paginate_aws_list(
            self.ecs_client, "list_tasks", "taskArns", cluster=cluster_name, serviceName=service_name
        )

    def get_task_info(self, cluster_name: str, service_name: str, desired_task_def_arn: str | None) -> list[TaskInfo]:
        task_arns = self.get_tasks(cluster_name, service_name)
        if not task_arns:
            return []

        response = self.ecs_client.describe_tasks(cluster=cluster_name, tasks=task_arns)
        tasks = response.get("tasks", [])
        return [_create_task_info(task, desired_task_def_arn) for task in tasks]

    def get_task_details(
        self, cluster_name: str, task_arn: str, desired_task_def_arn: str | None
    ) -> TaskDetails | None:
        result = self.get_task_and_definition(cluster_name, task_arn)
        if not result:
            return None

        task, task_definition = result
        is_desired_version = task["taskDefinitionArn"] == desired_task_def_arn
        return _build_task_details(task, task_definition, is_desired_version)

    def get_task_and_definition(
        self, cluster_name: str, task_arn: str
    ) -> tuple[TaskTypeDef, TaskDefinitionTypeDef] | None:
        task_response = self.ecs_client.describe_tasks(cluster=cluster_name, tasks=[task_arn])
        tasks = task_response.get("tasks", [])
        if not tasks:
            return None

        task = tasks[0]
        task_def_arn = task["taskDefinitionArn"]
        task_def_response = self.ecs_client.describe_task_definition(taskDefinition=task_def_arn)
        task_definition = task_def_response["taskDefinition"]

        return task, task_definition

    def _list_tasks_paginated(self, cluster_name: str, service_name: str | None, desired_status: str) -> list[str]:
        """List tasks with optional service name filtering."""
        kwargs = {"cluster": cluster_name, "desiredStatus": desired_status}
        if service_name:
            kwargs["serviceName"] = service_name
        return paginate_aws_list(self.ecs_client, "list_tasks", "taskArns", **kwargs)

    def get_task_history(self, cluster_name: str, service_name: str | None = None) -> list[TaskHistoryDetails]:
        """Get task history including stopped tasks with failure information."""
        task_arns = []

        running_arns = self._list_tasks_paginated(cluster_name, service_name, "RUNNING")
        task_arns.extend(running_arns)

        stopped_arns = self._list_tasks_paginated(cluster_name, service_name, "STOPPED")
        task_arns.extend(stopped_arns)

        if not task_arns:
            return []

        # Get detailed task information
        response = self.ecs_client.describe_tasks(cluster=cluster_name, tasks=task_arns)
        tasks = response.get("tasks", [])

        return [self._parse_task_history(task) for task in tasks]

    def get_task_failure_analysis(self, task_history: TaskHistoryDetails) -> str:
        """Analyze task failure and provide human-readable explanation."""
        if task_history["last_status"] == "RUNNING":
            return "✅ Task is currently running"

        stop_code = task_history["stop_code"]
        stopped_reason = task_history["stopped_reason"]

        # Check container exit codes
        for container in task_history["containers"]:
            exit_code = container["exit_code"]
            container_reason = container["reason"]

            if exit_code is not None and exit_code != 0:
                return self._analyze_container_failure(
                    container["name"], exit_code, container_reason, stop_code, stopped_reason
                )

        # No container failures, analyze task-level issues
        return self._analyze_task_failure(stop_code, stopped_reason)

    @staticmethod
    def _parse_task_history(task: TaskTypeDef) -> TaskHistoryDetails:
        """Parse task data into TaskHistoryDetails structure."""
        task_arn = task["taskArn"]
        task_def_arn = task["taskDefinitionArn"]
        task_def_family = task_def_arn.split("/")[-1].split(":")[0]
        task_def_revision = task_def_arn.split(":")[-1]

        containers = []
        for container in task.get("containers", []):
            containers.append(
                {
                    "name": container["name"],
                    "exit_code": container.get("exitCode"),
                    "reason": container.get("reason"),
                    "health_status": container.get("healthStatus"),
                    "last_status": container.get("lastStatus", "UNKNOWN"),
                }
            )

        return {
            "task_arn": task_arn,
            "task_definition_name": task_def_family,
            "task_definition_revision": task_def_revision,
            "last_status": task.get("lastStatus", "UNKNOWN"),
            "desired_status": task.get("desiredStatus", "UNKNOWN"),
            "stop_code": task.get("stopCode"),
            "stopped_reason": task.get("stoppedReason"),
            "created_at": task.get("createdAt"),
            "started_at": task.get("startedAt"),
            "stopped_at": task.get("stoppedAt"),
            "containers": containers,
        }

    @staticmethod
    def _analyze_container_failure(
        container_name: str,
        exit_code: int,
        container_reason: str | None,
        _stop_code: str | None,
        _stopped_reason: str | None,
    ) -> str:
        """Analyze container-level failure."""
        if exit_code == 137:
            if container_reason and "OutOfMemoryError" in container_reason:
                return f"🔴 Container '{container_name}' killed due to out of memory (OOM)"
            return f"⏰ Container '{container_name}' killed after timeout (exit code 137)"
        if exit_code == 139:
            return f"💥 Container '{container_name}' crashed with segmentation fault (exit code 139)"
        if exit_code == 143:
            return f"🛑 Container '{container_name}' gracefully stopped (SIGTERM)"
        if exit_code == 1:
            return f"❌ Container '{container_name}' application error (exit code 1)"
        reason_text = f" - {container_reason}" if container_reason else ""
        return f"🔴 Container '{container_name}' failed with exit code {exit_code}{reason_text}"

    @staticmethod
    def _analyze_task_failure(stop_code: str | None, stopped_reason: str | None) -> str:
        """Analyze task-level failure."""
        if not stop_code and not stopped_reason:
            return "✅ Task completed successfully"

        if stop_code == "TaskFailedToStart":
            if stopped_reason and "CannotPullContainerError" in stopped_reason:
                return "📦 Failed to pull container image - check image exists and permissions"
            if stopped_reason and "ResourcesNotAvailable" in stopped_reason:
                return "⚠️ Insufficient resources available to start task"
            reason_text = f" - {stopped_reason}" if stopped_reason else ""
            return f"🚫 Task failed to start{reason_text}"
        if stop_code == "ServiceSchedulerInitiated":
            return "🔄 Task stopped by service scheduler (deployment/scaling)"
        if stop_code == "SpotInterruption":
            return "💸 Task stopped due to spot instance interruption"
        if stop_code == "UserInitiated":
            return "👤 Task manually stopped by user"
        reason_text = f" - {stopped_reason}" if stopped_reason else ""
        code_text = f"({stop_code}) " if stop_code else ""
        return f"🔴 Task stopped {code_text}{reason_text}"


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
