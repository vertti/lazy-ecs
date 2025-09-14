"""UI layer - handles all user interaction and display logic."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import questionary
from rich.console import Console

from .aws_service import ECSService, TaskDetails

console = Console()


class ECSNavigator:
    """Navigator for interactive ECS exploration."""

    def __init__(self, ecs_service: ECSService) -> None:
        self.ecs_service = ecs_service

    def select_cluster(self) -> str:
        """Interactive cluster selection."""
        cluster_names = self.ecs_service.get_cluster_names()

        if not cluster_names:
            console.print("❌ No ECS clusters found", style="red")
            return ""

        selected = questionary.select(
            "Select an ECS cluster:",
            choices=cluster_names,
            style=questionary.Style(
                [
                    ("qmark", "fg:cyan bold"),
                    ("question", "bold"),
                    ("answer", "fg:cyan"),
                    ("pointer", "fg:cyan bold"),
                    ("highlighted", "fg:cyan"),
                    ("selected", "fg:green"),
                ]
            ),
        ).ask()

        return selected or ""

    def select_service(self, cluster_name: str) -> str:
        """Interactive service selection with status information."""
        service_info = self.ecs_service.get_service_info(cluster_name)

        if not service_info:
            console.print(f"❌ No services found in cluster '{cluster_name}'", style="red")
            return ""

        choices = [{"name": info["name"], "value": info["name"].split(" ")[1]} for info in service_info]

        selected = questionary.select(
            "Select a service:",
            choices=choices,
            style=questionary.Style(
                [
                    ("qmark", "fg:cyan bold"),
                    ("question", "bold"),
                    ("answer", "fg:cyan"),
                    ("pointer", "fg:cyan bold"),
                    ("highlighted", "fg:cyan"),
                    ("selected", "fg:green"),
                ]
            ),
        ).ask()

        return selected or ""

    def select_task(self, cluster_name: str, service_name: str) -> str:
        """Interactive task selection with auto-selection for single tasks."""
        task_info = self.ecs_service.get_task_info(cluster_name, service_name)

        if not task_info:
            console.print(f"❌ No tasks found for service '{service_name}'", style="red")
            return ""

        if len(task_info) == 1:
            task_arn = task_info[0]["value"]
            console.print(f"Auto-selected single task: {task_info[0]['name']}", style="green")
            return task_arn

        choices = [{"name": info["name"], "value": info["value"]} for info in task_info]

        selected = questionary.select(
            "Select a task:",
            choices=choices,
            style=questionary.Style(
                [
                    ("qmark", "fg:cyan bold"),
                    ("question", "bold"),
                    ("answer", "fg:cyan"),
                    ("pointer", "fg:cyan bold"),
                    ("highlighted", "fg:cyan"),
                    ("selected", "fg:green"),
                ]
            ),
        ).ask()

        return selected or ""

    def display_task_details(self, task_details: TaskDetails | None) -> None:
        """Display comprehensive task information."""
        if not task_details:
            console.print("❌ No task details available", style="red")
            return

        console.print("\n✅ Selected Task Details", style="bold green")
        console.print("=" * 60, style="dim")

        task_def_name = task_details["task_definition_name"]
        task_def_revision = task_details["task_definition_revision"]
        is_desired = task_details["is_desired_version"]
        desired_status = "✅ DESIRED" if is_desired else "🔴 NOT DESIRED"

        console.print(f"TASK_DEFINITION: {task_def_name}:{task_def_revision} {desired_status}", style="bold white")

        task_arn = task_details["task_arn"]
        task_id = task_arn.split("/")[-1]
        console.print(f"TASK_ID: {task_id[:8]}...", style="white")

        status = task_details["task_status"]
        console.print(f"STATUS: {status} | HEALTH: UNKNOWN", style="white")
        console.print("LAUNCH_TYPE: FARGATE | PLATFORM: 1.4.0", style="white")
        console.print("CPU: 512 | MEMORY: 2048MB", style="white")
        console.print("NETWORK: awsvpc", style="white")

        created_at = task_details.get("created_at")
        if created_at:
            created_str = created_at.strftime("%Y-%m-%d %H:%M:%S")
            console.print(f"CREATED: {created_str}", style="white")
        started_at = task_details.get("started_at")
        if started_at:
            started_str = started_at.strftime("%Y-%m-%d %H:%M:%S")
            console.print(f"STARTED: {started_str}", style="white")

        containers_count = len(task_details["containers"])
        console.print(f"\nCONTAINERS ({containers_count}):", style="bold white")
        for i, container in enumerate(task_details["containers"], 1):
            console.print(f"  [{i}] {container['name']}", style="cyan")
            console.print(f"      IMAGE: {container['image']}", style="white")
            if container["cpu"]:
                console.print(f"      CPU: {container['cpu']} units", style="dim")
            if container["memory"]:
                console.print(f"      MEMORY: {container['memory']}MB", style="dim")
            elif container.get("memoryReservation"):
                mem_res = container["memoryReservation"]
                console.print(f"      MEMORY_RESERVATION: {mem_res}MB", style="dim")

        console.print("=" * 60, style="dim")
        console.print("🎯 Task selected successfully!", style="blue")

    def select_task_feature(self, task_details: TaskDetails | None) -> str | None:
        """Present feature menu for the selected task."""
        if not task_details:
            return None

        containers = task_details.get("containers", [])

        if not containers:
            return None

        choices = _build_task_feature_choices(containers)

        selected = questionary.select(
            "Select a feature for this task:",
            choices=choices,
            style=questionary.Style(
                [
                    ("qmark", "fg:cyan bold"),
                    ("question", "bold"),
                    ("answer", "fg:cyan"),
                    ("pointer", "fg:cyan bold"),
                    ("highlighted", "fg:cyan"),
                    ("selected", "fg:green"),
                ]
            ),
        ).ask()

        return selected

    def show_container_logs(self, cluster_name: str, task_arn: str, container_name: str, lines: int = 50) -> None:
        """Display the last N lines of logs for a container."""
        log_config = self.ecs_service.get_log_config(cluster_name, task_arn, container_name)
        if not log_config:
            console.print(f"❌ Could not find log configuration for container '{container_name}'", style="red")
            console.print("Available log groups:", style="dim")
            log_groups = self.ecs_service.list_log_groups(cluster_name, container_name)
            for group in log_groups:
                console.print(f"  • {group}", style="cyan")
            return

        log_group_name = log_config["log_group"]
        log_stream_name = log_config["log_stream"]

        events = self.ecs_service.get_container_logs(log_group_name, log_stream_name, lines)

        if not events:
            console.print(
                f"📝 No logs found for container '{container_name}' in stream '{log_stream_name}'", style="yellow"
            )
            return

        console.print(f"\n📋 Last {len(events)} log entries for container '{container_name}':", style="bold cyan")
        console.print(f"Log group: {log_group_name}", style="dim")
        console.print(f"Log stream: {log_stream_name}", style="dim")
        console.print("=" * 80, style="dim")

        for event in events:
            timestamp = datetime.fromtimestamp(event["timestamp"] / 1000)
            message = event["message"].rstrip()
            console.print(f"[{timestamp.strftime('%H:%M:%S')}] {message}")

        console.print("=" * 80, style="dim")


def _build_task_feature_choices(containers: list[dict[str, Any]]) -> list[str]:
    """Build feature menu choices for containers plus exit option."""
    choices = []

    for container in containers:
        container_name = container["name"]
        choices.append(f"Show tail of logs for container: {container_name}")

    choices.append("Exit")

    return choices
