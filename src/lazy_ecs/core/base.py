"""Base classes for AWS services and UI components."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rich.console import Console

from .navigation import select_with_navigation

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
        return select_with_navigation(prompt, choices, back_text)

    def display_table(self, data: list[dict[str, Any]], title: str | None = None) -> None:
        """Display data in a formatted table (placeholder for future rich table)."""
        if title:
            self.console.print(f"\n{title}", style="bold cyan")

        for item in data:
            self.console.print(f"  {item}")
