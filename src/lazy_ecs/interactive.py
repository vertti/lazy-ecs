from __future__ import annotations

from datetime import datetime
from typing import Any, TypedDict, cast

import boto3
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
        cluster_names: list[str] = []
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

        service_names: list[str] = []
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
        container_images: list[str] = []
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

    def get_task_details(self, cluster_name: str, service_name: str, task_arn: str) -> dict[str, Any]:
        """Get comprehensive details for a specific task."""
        # Get task details
        task_response = self.ecs_client.describe_tasks(cluster=cluster_name, tasks=[task_arn])
        tasks = task_response.get("tasks", [])
        if not tasks:
            return {}

        task = tasks[0]
        task_def_arn = task["taskDefinitionArn"]

        # Get task definition details
        task_def_response = self.ecs_client.describe_task_definition(taskDefinition=task_def_arn)
        task_def = task_def_response["taskDefinition"]

        # Get service details for comparison
        service_response = self.ecs_client.describe_services(cluster=cluster_name, services=[service_name])
        services = service_response.get("services", [])
        desired_task_def = services[0]["taskDefinition"] if services else None

        # Extract container details
        containers = task_def.get("containerDefinitions", [])
        container_info = []
        for container in containers:
            container_info.append(
                {
                    "name": container.get("name", "unknown"),
                    "image": container.get("image", "unknown"),
                    "cpu": container.get("cpu", 0),
                    "memory": container.get("memory", 0),
                    "memoryReservation": container.get("memoryReservation"),
                }
            )

        # Extract task definition info
        task_def_name = task_def_arn.split("/")[-1].split(":")[0]
        task_def_revision = task_def_arn.split(":")[-1]
        is_desired_version = task_def_arn == desired_task_def

        return {
            "task_arn": task_arn,
            "task_id": task_arn.split("/")[-1],
            "task_definition_name": task_def_name,
            "task_definition_revision": task_def_revision,
            "task_definition_arn": task_def_arn,
            "is_desired_version": is_desired_version,
            "desired_task_definition": desired_task_def,
            "task_status": task.get("lastStatus", "unknown"),
            "health_status": task.get("healthStatus", "unknown"),
            "created_at": task.get("createdAt"),
            "started_at": task.get("startedAt"),
            "platform_version": task.get("platformVersion", "unknown"),
            "launch_type": task.get("launchType", "unknown"),
            "cpu_architecture": task_def.get("cpu", "unknown"),
            "memory": task_def.get("memory", "unknown"),
            "network_mode": task_def.get("networkMode", "unknown"),
            "containers": container_info,
            "tags": task.get("tags", []),
        }

    def display_task_details(self, task_details: dict[str, Any]) -> None:
        """Display comprehensive task details in a formatted way."""
        console.print("\n✅ Selected Task Details", style="bold green")
        console.print("=" * 60, style="dim")

        # Basic task info
        version_status = "✅ DESIRED" if task_details["is_desired_version"] else "🔴 WRONG VERSION"
        task_def_name = task_details["task_definition_name"]
        task_def_revision = task_details["task_definition_revision"]
        task_def_display = f"{task_def_name}:{task_def_revision}"
        console.print(f"TASK_DEFINITION: {task_def_display} {version_status}", style="white")
        console.print(f"TASK_ID: {task_details['task_id'][:16]}...", style="white")

        status_info = f"STATUS: {task_details['task_status']} | HEALTH: {task_details['health_status']}"
        console.print(status_info, style="white")

        launch_type = task_details["launch_type"]
        platform = task_details["platform_version"]
        launch_info = f"LAUNCH_TYPE: {launch_type} | PLATFORM: {platform}"
        console.print(launch_info, style="white")

        # Resource allocation
        cpu_mem = f"CPU: {task_details['cpu_architecture']} | MEMORY: {task_details['memory']}MB"
        console.print(cpu_mem, style="white")
        console.print(f"NETWORK: {task_details['network_mode']}", style="white")

        # Timestamps
        if task_details.get("created_at"):
            created_str = task_details["created_at"].strftime("%Y-%m-%d %H:%M:%S")
            console.print(f"CREATED: {created_str}", style="white")
        if task_details.get("started_at"):
            started_str = task_details["started_at"].strftime("%Y-%m-%d %H:%M:%S")
            console.print(f"STARTED: {started_str}", style="white")

        # Container details
        containers_count = len(task_details["containers"])
        console.print(f"\nCONTAINERS ({containers_count}):", style="bold white")
        for i, container in enumerate(task_details["containers"], 1):
            console.print(f"  [{i}] {container['name']}", style="cyan")
            console.print(f"      IMAGE: {container['image']}", style="white")
            if container["cpu"]:
                console.print(f"      CPU: {container['cpu']} units", style="dim")
            if container["memory"]:
                console.print(f"      MEMORY: {container['memory']}MB", style="dim")
            elif container.get("memoryReservation"):
                mem_res = container["memoryReservation"]
                console.print(f"      MEMORY_RESERVATION: {mem_res}MB", style="dim")

        console.print("=" * 60, style="dim")
        console.print("🎯 Task selected successfully!", style="blue")

    def select_task_feature(self, task_details: dict[str, Any]) -> str | None:
        """Present feature menu for the selected task."""
        containers = task_details.get("containers", [])

        if not containers:
            return None

        choices = _build_task_feature_choices(containers)

        selected = questionary.select(
            "Select a feature for this task:",
            choices=choices,
            style=questionary.Style(
                [
                    ("qmark", "fg:cyan bold"),
                    ("question", "bold"),
                    ("answer", "fg:cyan"),
                    ("pointer", "fg:cyan bold"),
                    ("highlighted", "fg:cyan"),
                    ("selected", "fg:green"),
                ]
            ),
        ).ask()

        return selected

    def show_container_logs(self, cluster_name: str, task_arn: str, container_name: str, lines: int = 50) -> None:
        """Display the last N lines of logs for a container."""
        logs_client = boto3.client("logs")

        log_config = _get_log_config_from_task(self.ecs_client, cluster_name, task_arn, container_name)
        if not log_config:
            console.print(f"❌ Could not find log configuration for container '{container_name}'", style="red")
            return

        log_group_name = log_config["log_group"]
        log_stream_name = log_config["log_stream"]

        try:
            response = logs_client.get_log_events(
                logGroupName=log_group_name, logStreamName=log_stream_name, limit=lines, startFromHead=False
            )

            events = response.get("events", [])

            if not events:
                console.print(
                    f"📝 No logs found for container '{container_name}' in stream '{log_stream_name}'", style="yellow"
                )
                return

            console.print(f"\n📋 Last {len(events)} log entries for container '{container_name}':", style="bold cyan")
            console.print(f"Log group: {log_group_name}", style="dim")
            console.print(f"Log stream: {log_stream_name}", style="dim")
            console.print("=" * 80, style="dim")

            for event in events:
                timestamp = datetime.fromtimestamp(event["timestamp"] / 1000)
                message = event["message"].rstrip()
                console.print(f"[{timestamp.strftime('%H:%M:%S')}] {message}")

            console.print("=" * 80, style="dim")

        except Exception as e:
            error_msg = f"Failed to fetch logs for container '{container_name}': {e}"
            console.print(f"❌ {error_msg}", style="red")


def _build_task_feature_choices(containers: list[dict[str, Any]]) -> list[str]:
    """Build feature menu choices for containers plus exit option."""
    choices = []

    # Add log tailing options for each container
    for container in containers:
        container_name = container["name"]
        choices.append(f"Show tail of logs for container: {container_name}")

    # Add exit option
    choices.append("Exit")

    return choices


def _get_log_config_from_task(
    ecs_client: ECSClient, cluster_name: str, task_arn: str, container_name: str
) -> dict[str, str] | None:
    """Get the actual log configuration from the ECS task definition."""
    try:
        # Get task details to find task definition
        task_response = ecs_client.describe_tasks(cluster=cluster_name, tasks=[task_arn])
        tasks = task_response.get("tasks", [])
        if not tasks:
            return None

        task = tasks[0]
        task_def_arn = task["taskDefinitionArn"]

        # Get task definition details
        task_def_response = ecs_client.describe_task_definition(taskDefinition=task_def_arn)
        task_definition = task_def_response["taskDefinition"]

        # Find the specific container
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

                # Build log stream name: prefix/container_name/task_id
                task_id = task_arn.split("/")[-1]
                log_stream = f"{stream_prefix}/{container_name}/{task_id}"

                return {"log_group": log_group, "log_stream": log_stream}

    except Exception:
        pass

    return None


def _list_log_groups(logs_client, cluster_name: str, container_name: str) -> None:
    """List available log groups to help with debugging."""
    try:
        response = logs_client.describe_log_groups(limit=50)
        groups = response.get("logGroups", [])

        if groups:
            console.print("  Recent log groups:")
            for group in groups[:10]:
                name = group["logGroupName"]
                if (
                    cluster_name.lower() in name.lower()
                    or container_name.lower() in name.lower()
                    or "ecs" in name.lower()
                ):
                    console.print(f"    • {name}", style="cyan")
                else:
                    console.print(f"    • {name}", style="dim")
        else:
            console.print("  No log groups found")

    except Exception as e:
        console.print(f"  Could not list log groups: {e}", style="dim")
