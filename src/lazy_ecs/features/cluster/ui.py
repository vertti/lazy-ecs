"""UI components for cluster operations."""

from __future__ import annotations

from rich.console import Console

from ...core.base import BaseUIComponent
from ...core.navigation import select_with_navigation
from .cluster import ClusterService

console = Console()


class ClusterUI(BaseUIComponent):
    """UI component for cluster selection and display."""

    def __init__(self, cluster_service: ClusterService) -> None:
        super().__init__()
        self.cluster_service = cluster_service

    def select_cluster(self) -> str:
        """Interactive cluster selection."""
        cluster_names = self.cluster_service.get_cluster_names()

        if not cluster_names:
            console.print("❌ No ECS clusters found", style="red")
            return ""

        # Convert cluster names to choice format (top-level menu gets both Back and Exit, but Back will just exit)
        choices = [{"name": name, "value": name} for name in cluster_names]

        selected = select_with_navigation(
            "Select an ECS cluster:",
            choices,
            "Exit",  # This will show as "Back: Exit" but ESC and 'b' will both act like exit at top level
        )

        return selected or ""
