from __future__ import annotations

from datetime import datetime
from typing import Any, TypedDict, cast

import questionary
from mypy_boto3_ecs.client import ECSClient
from mypy_boto3_ecs.type_defs import ServiceTypeDef, TaskDefinitionTypeDef, TaskTypeDef
from rich.console import Console

console = Console()


class ServiceChoice(TypedDict):
    name: str
    value: str
    status: str
    running_count: int
    desired_count: int
    pending_count: int


class TaskChoice(TypedDict):
    name: str
    value: str
    task_def_arn: str
    is_desired: bool
    revision: str
    images: list[str]
    created_at: datetime | None


class ECSNavigator:
    def __init__(self, ecs_client: ECSClient) -> None:
        self.ecs_client = ecs_client

    def get_cluster_names(self) -> list[str]:
        """Get list of ECS cluster names from AWS."""
        response = self.ecs_client.list_clusters()
        cluster_arns = response.get("clusterArns", [])

        # Extract cluster name from ARN (last part after '/')
        cluster_names = []
        for arn in cluster_arns:
            cluster_name = arn.split("/")[-1]
            cluster_names.append(cluster_name)

        return cluster_names

    def select_cluster(self) -> str:
        """Interactive cluster selection with arrow keys."""
        clusters = self.get_cluster_names()

        if not clusters:
            console.print("No ECS clusters found!", style="red")
            return ""

        selected_cluster = questionary.select(
            "Select an ECS cluster:",
            choices=clusters,
            style=questionary.Style(
                [
                    ("selected", "fg:#61ffca bold"),
                    ("pointer", "fg:#61ffca bold"),
                    ("question", "fg:#ffffff bold"),
                ]
            ),
        ).ask()

        return selected_cluster or ""

    def get_services(self, cluster_name: str) -> list[str]:
        """Get list of ECS service names from specific cluster."""
        response = self.ecs_client.list_services(cluster=cluster_name)
        service_arns = response.get("serviceArns", [])

        service_names = []
        for arn in service_arns:
            service_name = arn.split("/")[-1]
            service_names.append(service_name)

        return service_names

    def _determine_service_status(self, running_count: int, desired_count: int, pending_count: int) -> tuple[str, str]:
        """Determine service health status icon and text."""
        if running_count == desired_count and pending_count == 0:
            return "✅", "HEALTHY"
        elif running_count < desired_count:
            return "⚠️ ", "SCALING"
        elif running_count > desired_count:
            return "🔄", "DRAINING"
        else:
            return "❌", "UNHEALTHY"

    def _format_service_state_info(self, running_count: int, desired_count: int, pending_count: int) -> str:
        """Format service state information string."""
        state_info = f"({running_count}/{desired_count})"
        if pending_count > 0:
            state_info = f"({running_count}/{desired_count}, {pending_count} pending)"
        return state_info

    def _create_service_choice(self, service: ServiceTypeDef) -> ServiceChoice:
        """Create a formatted service choice with state info."""
        service_name = service["serviceName"]
        desired_count = service["desiredCount"]
        running_count = service["runningCount"]
        pending_count = service["pendingCount"]

        status_icon, status_text = self._determine_service_status(running_count, desired_count, pending_count)
        state_info = self._format_service_state_info(running_count, desired_count, pending_count)
        display_name = f"{status_icon} {service_name} {state_info} - {status_text}"

        return ServiceChoice(
            name=display_name,
            value=service_name,
            status=status_text,
            running_count=running_count,
            desired_count=desired_count,
            pending_count=pending_count,
        )

    def get_service_choices(self, cluster_name: str) -> list[ServiceChoice]:
        """Get services with detailed state information for interactive selection."""
        response = self.ecs_client.list_services(cluster=cluster_name)
        service_arns = response.get("serviceArns", [])

        if not service_arns:
            return []

        # Get detailed service information
        describe_response = self.ecs_client.describe_services(cluster=cluster_name, services=service_arns)
        services = describe_response.get("services", [])

        # Create choices
        choices = [self._create_service_choice(service) for service in services]

        # Sort unhealthy services first
        choices.sort(key=lambda x: (x["status"] == "HEALTHY", x["name"]))
        return choices

    def select_service(self, cluster_name: str) -> str:
        """Interactive service selection with arrow keys and state information."""
        service_choices = self.get_service_choices(cluster_name)

        if not service_choices:
            console.print(f"No services found in cluster '{cluster_name}'!", style="red")
            return ""

        # Show summary of unhealthy services
        unhealthy_services = [s for s in service_choices if s["status"] != "HEALTHY"]
        if unhealthy_services:
            console.print(f"\n⚠️  {len(unhealthy_services)} service(s) not in desired state:", style="bold yellow")
            for service in unhealthy_services:
                console.print(
                    f"  • {service['value']}: {service['running_count']}/{service['desired_count']}", style="yellow"
                )
            console.print()

        selected_service = questionary.select(
            f"Select a service from '{cluster_name}' (unhealthy services shown first):",
            choices=cast(list[dict[str, Any]], service_choices),
            style=questionary.Style(
                [
                    ("selected", "fg:#61ffca bold"),
                    ("pointer", "fg:#61ffca bold"),
                    ("question", "fg:#ffffff bold"),
                ]
            ),
        ).ask()

        return selected_service or ""

    def get_tasks(self, cluster_name: str, service_name: str) -> list[str]:
        """Get list of running task ARNs for a specific service."""
        response = self.ecs_client.list_tasks(cluster=cluster_name, serviceName=service_name)
        task_arns = response.get("taskArns", [])
        return task_arns

    def select_task(self, cluster_name: str, service_name: str) -> str:
        """Select task - auto-select if single task, interactive if multiple."""
        task_choices = self.get_readable_task_choices(cluster_name, service_name)

        if not task_choices:
            console.print(f"No running tasks found for service '{service_name}'!", style="red")
            return ""

        # Show summary of version mismatches
        mismatched_tasks = [t for t in task_choices if not t["is_desired"]]
        if mismatched_tasks:
            console.print(f"\n🔴 {len(mismatched_tasks)} task(s) running wrong task definition:", style="bold red")
            for task in mismatched_tasks:
                images = ", ".join(task["images"]) if task["images"] else "unknown"
                console.print(f"  • Task v{task['revision']}: {images}", style="red")
            console.print()

        if len(task_choices) == 1:
            choice = task_choices[0]
            if choice["is_desired"]:
                console.print(f"Auto-selected single task: {choice['name']}", style="dim")
            else:
                console.print(f"⚠️  Auto-selected single task (WRONG VERSION): {choice['name']}", style="bold yellow")
            return choice["value"]

        selected_task = questionary.select(
            f"Select a task from '{service_name}' (wrong versions shown first):",
            choices=cast(list[dict[str, Any]], task_choices),
            style=questionary.Style(
                [
                    ("selected", "fg:#61ffca bold"),
                    ("pointer", "fg:#61ffca bold"),
                    ("question", "fg:#ffffff bold"),
                ]
            ),
        ).ask()

        return selected_task or ""

    def _get_desired_task_definition(self, cluster_name: str, service_name: str) -> str | None:
        """Get the service's desired task definition ARN."""
        service_response = self.ecs_client.describe_services(cluster=cluster_name, services=[service_name])
        services = service_response.get("services", [])
        return services[0]["taskDefinition"] if services else None

    def _get_task_definition_details(self, task_def_arns: list[str]) -> dict[str, TaskDefinitionTypeDef]:
        """Fetch task definition details for multiple ARNs."""
        task_def_details: dict[str, TaskDefinitionTypeDef] = {}
        for task_def_arn in task_def_arns:
            try:
                response = self.ecs_client.describe_task_definition(taskDefinition=task_def_arn)
                task_def_details[task_def_arn] = response["taskDefinition"]
            except Exception:
                pass
        return task_def_details

    def _extract_container_images(
        self, task_def_details: dict[str, TaskDefinitionTypeDef], task_def_arn: str
    ) -> list[str]:
        """Extract container images from task definition."""
        container_images = []
        if task_def_arn in task_def_details:
            containers = task_def_details[task_def_arn].get("containerDefinitions", [])
            for container in containers:
                image = container.get("image", "unknown")
                # Shorten image name (just repo:tag, not full registry)
                if "/" in image:
                    image = image.split("/")[-1]
                container_images.append(image)
        return container_images

    def _create_task_choice(
        self, task: TaskTypeDef, desired_task_def: str | None, task_def_details: dict[str, TaskDefinitionTypeDef]
    ) -> TaskChoice:
        """Create a formatted task choice with version and image info."""
        task_arn = task["taskArn"]
        task_def_arn = task["taskDefinitionArn"]

        # Extract task definition info
        task_def_name = task_def_arn.split("/")[-1].split(":")[0]
        task_def_revision = task_def_arn.split(":")[-1]

        # Check if this task is using the desired task definition
        is_desired = task_def_arn == desired_task_def
        version_indicator = f"🔴 v{task_def_revision}" if not is_desired else f"✅ v{task_def_revision}"

        # Get container images
        container_images = self._extract_container_images(task_def_details, task_def_arn)
        images_str = ", ".join(container_images) if container_images else "unknown"

        # Format timestamp
        created_at = task.get("createdAt")
        created_str = created_at.strftime("%H:%M:%S") if created_at else "unknown"

        # Create display name
        task_id_short = task_arn.split("/")[-1][:8]
        display_name = f"{version_indicator} {task_def_name} ({task_id_short}) - {images_str} - {created_str}"

        return TaskChoice(
            name=display_name,
            value=task_arn,
            task_def_arn=task_def_arn,
            is_desired=is_desired,
            revision=task_def_revision,
            images=container_images,
            created_at=created_at,
        )

    def get_readable_task_choices(self, cluster_name: str, service_name: str) -> list[TaskChoice]:
        """Get list of tasks with human-readable names and task definition info for interactive selection."""
        task_arns = self.get_tasks(cluster_name, service_name)
        if not task_arns:
            return []

        # Get service's desired task definition
        desired_task_def = self._get_desired_task_definition(cluster_name, service_name)

        # Get detailed task information
        response = self.ecs_client.describe_tasks(cluster=cluster_name, tasks=task_arns)
        tasks = response.get("tasks", [])

        # Get task definition details
        task_def_arns = list({task["taskDefinitionArn"] for task in tasks})
        task_def_details = self._get_task_definition_details(task_def_arns)

        # Create choices
        choices = [self._create_task_choice(task, desired_task_def, task_def_details) for task in tasks]

        # Sort by: wrong version first, then by creation time (newest first)
        choices.sort(key=lambda x: (x["is_desired"], -(x["created_at"].timestamp() if x["created_at"] else 0)))
        return choices
