"""Base classes for AWS services and UI components."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import questionary
from rich.console import Console

if TYPE_CHECKING:
    from mypy_boto3_ecs.client import ECSClient


class BaseAWSService:
    """Base class for AWS service interactions with common patterns."""

    def __init__(self, ecs_client: ECSClient) -> None:
        self.ecs_client = ecs_client


class BaseUIComponent:
    """Base class for UI components with common patterns."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def select_with_nav(self, prompt: str, choices: list[dict[str, str]], back_text: str) -> str | None:
        """Standard selection with back/exit navigation."""
        # Add navigation choices
        nav_choices = [
            *choices,
            {"name": f"⬅️ {back_text}", "value": "navigation:back"},
            {"name": "❌ Exit", "value": "navigation:exit"},
        ]

        return questionary.select(
            prompt,
            choices=nav_choices,
            style=self._get_questionary_style(),
        ).ask()

    def _get_questionary_style(self) -> questionary.Style:
        """Consistent questionary styling across all prompts."""
        return questionary.Style(
            [
                ("qmark", "fg:cyan bold"),
                ("question", "bold"),
                ("answer", "fg:cyan"),
                ("pointer", "fg:cyan bold"),
                ("highlighted", "fg:cyan"),
                ("selected", "fg:green"),
            ]
        )

    def display_table(self, data: list[dict[str, Any]], title: str | None = None) -> None:
        """Display data in a formatted table (placeholder for future rich table)."""
        if title:
            self.console.print(f"\n{title}", style="bold cyan")

        for item in data:
            self.console.print(f"  {item}")
