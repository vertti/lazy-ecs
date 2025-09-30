"""UI components for cluster operations."""

from __future__ import annotations

from rich.console import Console

from ...core.base import BaseUIComponent
from ...core.navigation import handle_navigation, select_with_auto_pagination
from ...core.utils import show_spinner
from .cluster import ClusterService

console = Console()


class ClusterUI(BaseUIComponent):
    """UI component for cluster selection and display."""

    def __init__(self, cluster_service: ClusterService) -> None:
        super().__init__()
        self.cluster_service = cluster_service

    def select_cluster(self) -> str:
        with show_spinner():
            cluster_names = self.cluster_service.get_cluster_names()

        if not cluster_names:
            console.print("❌ No ECS clusters found", style="red")
            return ""

        choices = [{"name": name, "value": name} for name in cluster_names]

        selected = select_with_auto_pagination("Select an ECS cluster:", choices, None)

        should_continue, _should_exit = handle_navigation(selected)
        if not should_continue:
            return ""

        return selected or ""
