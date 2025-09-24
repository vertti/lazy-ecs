"""UI components for service operations."""

from __future__ import annotations

import questionary
from rich.console import Console
from rich.table import Table

from ...core.base import BaseUIComponent
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

        return self.select_with_nav("Select a service:", choices, "Back to cluster selection")

    def select_service_action(self, service_name: str, task_info: list[TaskInfo]) -> str | None:
        """Present service action menu."""
        choices = []

        for task in task_info:
            choices.append({"name": task["name"], "value": f"task:show_details:{task['value']}"})

        choices.append({"name": "📋 Show service events", "value": "action:show_events"})
        choices.append({"name": "🚀 Force new deployment", "value": "action:force_deployment"})

        return self.select_with_nav(
            f"Select action for service '{service_name}':", choices, "Back to cluster selection"
        )

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

    def display_service_events(self, cluster_name: str, service_name: str) -> None:
        """Display service events in a Rich table."""
        events = self.service_service.get_service_events(cluster_name, service_name)

        if not events:
            console.print(f"No events found for service '{service_name}'", style="blue")
            return

        table = Table(title=f"Service Events: {service_name}")
        table.add_column("Time", style="cyan", no_wrap=True)
        table.add_column("Type", style="magenta", width=12)
        table.add_column("Message", style="white")

        for event in events[:20]:  # Show most recent 20 events
            created_at = event["created_at"]
            time_str = created_at.strftime("%m/%d %H:%M") if created_at else "Unknown"

            event_type = event["event_type"]
            type_style = _get_event_type_style(event_type)
            type_display = f"[{type_style}]{event_type.title()}[/{type_style}]"

            message = event["message"]
            if len(message) > 80:
                message = message[:77] + "..."

            table.add_row(time_str, type_display, message)

        console.print(table)


def _get_event_type_style(event_type: str) -> str:
    """Get Rich style for event type."""
    event_styles = {
        "deployment": "blue",
        "scaling": "yellow",
        "failure": "red",
        "other": "white",
    }
    return event_styles.get(event_type, "white")
