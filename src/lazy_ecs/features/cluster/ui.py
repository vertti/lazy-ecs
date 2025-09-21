"""UI components for cluster operations."""

from __future__ import annotations

import questionary
from rich.console import Console

from ...core.base import BaseUIComponent
from ...core.navigation import get_questionary_style
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

        # Convert cluster names to choice format and add Exit (top-level, no Back needed)
        choices = [{"name": name, "value": name} for name in cluster_names]
        choices.append({"name": "❌ Exit", "value": "navigation:exit"})

        selected = questionary.select(
            "Select an ECS cluster:",
            choices=choices,
            style=get_questionary_style(),
        ).ask()

        return selected or ""
