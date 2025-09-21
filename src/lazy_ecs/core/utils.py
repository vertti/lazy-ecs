"""Utility functions for lazy-ecs."""

from __future__ import annotations

from rich.console import Console

console = Console()


def extract_name_from_arn(arn: str) -> str:
    """Extract resource name from AWS ARN."""
    return arn.split("/")[-1]


def determine_service_status(running_count: int, desired_count: int, pending_count: int) -> tuple[str, str]:
    """Determine service status icon and text."""
    if running_count == desired_count and pending_count == 0:
        return "✅", "HEALTHY"
    if running_count < desired_count:
        return "⚠️", "SCALING"
    if running_count > desired_count:
        return "🔴", "OVER_SCALED"
    return "🟡", "PENDING"


def print_error(message: str) -> None:
    console.print(f"❌ {message}", style="red")


def print_success(message: str) -> None:
    console.print(f"✅ {message}", style="green")


def print_warning(message: str) -> None:
    console.print(f"⚠️ {message}", style="yellow")


def print_info(message: str) -> None:
    console.print(message, style="blue")
