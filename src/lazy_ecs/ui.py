"""UI layer - handles all user interaction and display logic."""

from __future__ import annotations

from typing import Any

from rich.console import Console

from .aws_service import ECSService
from .core.base import BaseUIComponent
from .core.navigation import add_navigation_choices
from .core.types import TaskDetails
from .core.utils import show_spinner
from .features.cluster.cluster import ClusterService
from .features.cluster.ui import ClusterUI
from .features.container.ui import ContainerUI
from .features.service.ui import ServiceUI
from .features.task.ui import TaskUI

console = Console()


class ECSNavigator(BaseUIComponent):
    """Navigator for interactive ECS exploration."""

    def __init__(self, ecs_service: ECSService) -> None:
        super().__init__()
        self.ecs_service = ecs_service
        # Initialize feature UI components
        cluster_service = ClusterService(ecs_service.ecs_client)
        self._cluster_ui = ClusterUI(cluster_service)

        # Initialize service UI components using existing service instances from ECSService
        self._service_ui = ServiceUI(ecs_service._service, ecs_service._service_actions)

        # Initialize task UI components
        self._task_ui = TaskUI(ecs_service._task)

        # Initialize container UI components
        self._container_ui = ContainerUI(ecs_service._container)

    def select_cluster(self) -> str:
        """Interactive cluster selection."""
        return self._cluster_ui.select_cluster()

    def select_service(self, cluster_name: str) -> str | None:
        """Interactive service selection with status information and navigation."""
        return self._service_ui.select_service(cluster_name)

    def select_service_action(self, cluster_name: str, service_name: str) -> str | None:
        """Interactive selection combining tasks and service-level actions."""
        with show_spinner():
            task_info = self.ecs_service.get_task_info(cluster_name, service_name)
        return self._service_ui.select_service_action(service_name, task_info)

    def select_task(self, cluster_name: str, service_name: str) -> str:
        """Interactive task selection - no auto-selection since users need to see service actions too."""
        with show_spinner():
            task_info = self.ecs_service.get_task_info(cluster_name, service_name)

        if not task_info:
            console.print(f"❌ No tasks found for service '{service_name}'", style="red")
            return ""

        choices = [{"name": info["name"], "value": info["value"]} for info in task_info]

        selected = self.select_with_nav("Select a task:", choices, "Back to service selection")

        return selected or ""

    def display_task_details(self, task_details: TaskDetails | None) -> None:
        return self._task_ui.display_task_details(task_details)

    def select_task_feature(self, task_details: TaskDetails | None) -> str | None:
        return self._task_ui.select_task_feature(task_details)

    def show_container_logs_live_tail(self, cluster_name: str, task_arn: str, container_name: str) -> None:
        """Display recent logs then stream new logs for a container."""
        return self._container_ui.show_logs_live_tail(cluster_name, task_arn, container_name)

    def show_container_environment_variables(self, cluster_name: str, task_arn: str, container_name: str) -> None:
        return self._container_ui.show_container_environment_variables(cluster_name, task_arn, container_name)

    def show_container_secrets(self, cluster_name: str, task_arn: str, container_name: str) -> None:
        return self._container_ui.show_container_secrets(cluster_name, task_arn, container_name)

    def show_container_port_mappings(self, cluster_name: str, task_arn: str, container_name: str) -> None:
        return self._container_ui.show_container_port_mappings(cluster_name, task_arn, container_name)

    def show_container_volume_mounts(self, cluster_name: str, task_arn: str, container_name: str) -> None:
        return self._container_ui.show_container_volume_mounts(cluster_name, task_arn, container_name)

    def handle_force_deployment(self, cluster_name: str, service_name: str) -> None:
        return self._service_ui.handle_force_deployment(cluster_name, service_name)

    def show_service_events(self, cluster_name: str, service_name: str) -> None:
        return self._service_ui.display_service_events(cluster_name, service_name)

    def show_service_metrics(self, cluster_name: str, service_name: str) -> None:
        """Fetch and display service metrics."""
        with show_spinner():
            metrics = self.ecs_service.get_service_metrics(cluster_name, service_name, hours=1)

        if metrics:
            self._service_ui.display_service_metrics(service_name, metrics)
        else:
            console.print(f"\n⚠️ No metrics available for service '{service_name}'", style="yellow")
            console.print("This could mean:", style="dim")
            console.print("  - The service has no running tasks", style="dim")
            console.print("  - CloudWatch metrics are not yet available", style="dim")
            console.print("  - The service was recently created", style="dim")

    def show_task_history(self, cluster_name: str, service_name: str) -> None:
        self._task_ui.display_task_history(cluster_name, service_name)


def _build_task_feature_choices(containers: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Build feature menu choices for containers plus navigation options."""
    actions = [
        ("Show logs (tail) for container: {name}", "container_action", "tail_logs"),
        ("Show environment variables for container: {name}", "container_action", "show_env"),
        ("Show secrets for container: {name}", "container_action", "show_secrets"),
        ("Show port mappings for container: {name}", "container_action", "show_ports"),
        ("Show volume mounts for container: {name}", "container_action", "show_volumes"),
    ]

    choices = []

    # Add container actions
    for display_template, action_type, action_name in actions:
        for container in containers:
            container_name = container["name"]
            choices.append(
                {
                    "name": display_template.format(name=container_name),
                    "value": f"{action_type}:{action_name}:{container_name}",
                }
            )

    # Add navigation options
    return add_navigation_choices(choices, "Back to service selection")
