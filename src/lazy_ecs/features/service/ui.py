"""UI components for service operations."""

from __future__ import annotations

import questionary
from rich.console import Console

from ...core.base import BaseUIComponent
from ...core.navigation import add_navigation_choices, get_questionary_style
from ...core.types import TaskInfo
from .actions import ServiceActions
from .service import ServiceService

console = Console()


class ServiceUI(BaseUIComponent):
    """UI component for service selection and display."""

    def __init__(self, service_service: ServiceService, service_actions: ServiceActions) -> None:
        super().__init__()
        self.service_service = service_service
        self.service_actions = service_actions

    def select_service(self, cluster_name: str) -> str | None:
        """Interactive service selection with status information and navigation."""
        service_info = self.service_service.get_service_info(cluster_name)

        if not service_info:
            console.print(f"❌ No services found in cluster '{cluster_name}'", style="red")
            return "navigation:back"

        choices = [{"name": info["name"], "value": f"service:{info['name'].split(' ')[1]}"} for info in service_info]
        choices = add_navigation_choices(choices, "Back to cluster selection")

        return questionary.select(
            "Select a service:",
            choices=choices,
            style=get_questionary_style(),
        ).ask()

    def select_service_action(self, service_name: str, task_info: list[TaskInfo]) -> str | None:
        """Present service action menu."""
        choices = []

        for task in task_info:
            choices.append({"name": task["name"], "value": f"task:show_details:{task['value']}"})

        choices.append({"name": "🚀 Force new deployment", "value": "action:force_deployment"})

        choices = add_navigation_choices(choices, "Back to cluster selection")

        return questionary.select(
            f"Select action for service '{service_name}':",
            choices=choices,
            style=get_questionary_style(),
        ).ask()

    def handle_force_deployment(self, cluster_name: str, service_name: str) -> None:
        """Handle force deployment confirmation and execution."""
        confirm = questionary.confirm(
            f"Force new deployment for service '{service_name}' in cluster '{cluster_name}'?"
        ).ask()

        if confirm:
            success = self.service_actions.force_new_deployment(cluster_name, service_name)
            if success:
                console.print(f"✅ Successfully triggered deployment for '{service_name}'", style="green")
            else:
                console.print(f"❌ Failed to trigger deployment for '{service_name}'", style="red")
