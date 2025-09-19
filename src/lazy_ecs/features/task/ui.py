"""UI components for task operations."""

from __future__ import annotations

from typing import Any

import questionary
from rich.console import Console
from rich.table import Table

from ...core.base import BaseUIComponent
from ...core.navigation import add_navigation_choices, get_questionary_style
from ...core.types import TaskDetails
from .task import TaskService

console = Console()


class TaskUI(BaseUIComponent):
    """UI component for task selection and display."""

    def __init__(self, task_service: TaskService) -> None:
        super().__init__()
        self.task_service = task_service

    def select_task(self, cluster_name: str, service_name: str, desired_task_def_arn: str | None) -> str:
        """Interactive task selection."""
        task_info = self.task_service.get_task_info(cluster_name, service_name, desired_task_def_arn)

        if not task_info:
            console.print(f"❌ No tasks found for service '{service_name}' in cluster '{cluster_name}'", style="red")
            return ""

        if len(task_info) == 1:
            console.print(f"🎯 Auto-selected single task: {task_info[0]['name']}", style="cyan")
            return task_info[0]["value"]

        choices = [{"name": task["name"], "value": task["value"]} for task in task_info]

        selected = questionary.select(
            "Select a task:",
            choices=choices,
            style=get_questionary_style(),
        ).ask()

        if selected:
            console.print("🎯 Task selected successfully!", style="blue")
            return selected

        return ""

    def display_task_details(self, task_details: TaskDetails | None) -> None:
        """Display comprehensive task details."""
        if not task_details:
            return

        console.print(f"\n📋 Task Details: {task_details['task_definition_name']}", style="bold cyan")
        console.print("=" * 80, style="dim")

        # Basic info
        console.print(f"Task ARN: {task_details['task_arn']}", style="white")
        console.print(
            f"Task Definition: {task_details['task_definition_name']}:{task_details['task_definition_revision']}",
            style="white",
        )
        console.print(f"Status: {task_details['task_status']}", style="white")

        # Version status
        version_status = "✅ Desired version" if task_details["is_desired_version"] else "🔴 Outdated version"
        console.print(f"Version: {version_status}", style="green" if task_details["is_desired_version"] else "red")

        # Timestamps
        created_at = task_details.get("created_at")
        started_at = task_details.get("started_at")
        if created_at:
            console.print(f"Created: {created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}", style="white")
        if started_at:
            console.print(f"Started: {started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}", style="white")

        # Container info
        containers = task_details.get("containers", [])
        if containers:
            console.print(f"\n📦 Containers ({len(containers)}):", style="bold cyan")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Name", style="cyan")
            table.add_column("Image", style="yellow")
            table.add_column("CPU", style="green")
            table.add_column("Memory", style="blue")

            for container in containers:
                cpu = str(container.get("cpu", "N/A"))
                memory = str(container.get("memory", "N/A"))
                memory_reservation = container.get("memoryReservation")
                if memory_reservation and memory == "N/A":
                    memory = f"{memory_reservation} (soft)"

                table.add_row(
                    container["name"],
                    container["image"],
                    cpu,
                    memory,
                )

            console.print(table)

        console.print("=" * 80, style="dim")

    def select_task_feature(self, task_details: TaskDetails | None) -> str | None:
        """Present feature menu for the selected task."""
        if not task_details:
            return None

        containers = task_details.get("containers", [])

        if not containers:
            return None

        choices = _build_task_feature_choices(containers)

        return questionary.select(
            "Select a feature for this task:",
            choices=choices,
            style=get_questionary_style(),
        ).ask()


def _build_task_feature_choices(containers: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Build feature choices for containers."""
    choices = []

    for container in containers:
        container_name = container["name"]

        # Add container features
        choices.extend(
            [
                {
                    "name": f"📋 Show logs for '{container_name}'",
                    "value": f"container_action:show_logs:{container_name}",
                },
                {
                    "name": f"🔧 Show environment variables for '{container_name}'",
                    "value": f"container_action:show_env:{container_name}",
                },
                {
                    "name": f"🔐 Show secrets for '{container_name}'",
                    "value": f"container_action:show_secrets:{container_name}",
                },
                {
                    "name": f"🌐 Show port mappings for '{container_name}'",
                    "value": f"container_action:show_ports:{container_name}",
                },
                {
                    "name": f"💾 Show volume mounts for '{container_name}'",
                    "value": f"container_action:show_volumes:{container_name}",
                },
            ]
        )

    add_navigation_choices(choices, "Back to service selection")
    return choices
