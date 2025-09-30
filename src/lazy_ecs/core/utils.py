"""Utility functions for lazy-ecs."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Literal

from rich.console import Console
from rich.spinner import Spinner

if TYPE_CHECKING:
    from mypy_boto3_ecs.client import ECSClient

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


@contextmanager
def show_spinner() -> Iterator[None]:
    """Context manager that shows a spinner while running operations."""
    spinner = Spinner("dots", style="cyan")
    with console.status(spinner):
        yield


def paginate_aws_list(
    client: ECSClient,
    operation_name: Literal[
        "list_account_settings",
        "list_attributes",
        "list_clusters",
        "list_container_instances",
        "list_services_by_namespace",
        "list_services",
        "list_task_definition_families",
        "list_task_definitions",
        "list_tasks",
    ],
    result_key: str,
    **kwargs: str,
) -> list[str]:
    paginator = client.get_paginator(operation_name)  # type: ignore[no-matching-overload]
    page_iterator = paginator.paginate(**kwargs)

    results: list[str] = []
    for page in page_iterator:
        results.extend(page.get(result_key, []))

    return results
