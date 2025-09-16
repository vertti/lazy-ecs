"""UI layer - handles all user interaction and display logic."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import questionary
from rich.console import Console

from .aws_service import ECSService, TaskDetails

console = Console()

# Consistent questionary styling across all prompts
QUESTIONARY_STYLE = questionary.Style(
    [
        ("qmark", "fg:cyan bold"),
        ("question", "bold"),
        ("answer", "fg:cyan"),
        ("pointer", "fg:cyan bold"),
        ("highlighted", "fg:cyan"),
        ("selected", "fg:green"),
    ]
)


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
            style=QUESTIONARY_STYLE,
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
            style=QUESTIONARY_STYLE,
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
            style=QUESTIONARY_STYLE,
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

        return questionary.select(
            "Select a feature for this task:",
            choices=choices,
            style=QUESTIONARY_STYLE,
        ).ask()

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

    def show_container_environment_variables(self, cluster_name: str, task_arn: str, container_name: str) -> None:
        """Display environment variables for a container."""
        env_vars = self.ecs_service.get_container_environment_variables(cluster_name, task_arn, container_name)

        if env_vars is None:
            console.print(f"❌ Could not find environment variables for container '{container_name}'", style="red")
            return

        if not env_vars:
            console.print(f"📝 No environment variables found for container '{container_name}'", style="yellow")
            return

        console.print(f"\n🔧 Environment variables for container '{container_name}':", style="bold cyan")
        console.print("=" * 60, style="dim")

        sorted_vars = sorted(env_vars.items())

        for name, value in sorted_vars:
            display_value = value if len(value) <= 80 else f"{value[:77]}..."
            console.print(f"{name}={display_value}", style="white")

        console.print("=" * 60, style="dim")
        console.print(f"📊 Total: {len(env_vars)} environment variables", style="blue")

    def show_container_secrets(self, cluster_name: str, task_arn: str, container_name: str) -> None:
        """Display secrets configuration for a container."""
        secrets = self.ecs_service.get_container_secrets(cluster_name, task_arn, container_name)

        if secrets is None:
            console.print(f"❌ Could not find secrets configuration for container '{container_name}'", style="red")
            return

        if not secrets:
            console.print(f"🔐 No secrets configured for container '{container_name}'", style="yellow")
            return

        console.print(f"\n🔐 Secrets for container '{container_name}' (values not shown):", style="bold magenta")
        console.print("=" * 60, style="dim")

        sorted_secrets = sorted(secrets.items())

        for name, value_from in sorted_secrets:
            if "secretsmanager" in value_from:
                parts = value_from.split(":")
                if len(parts) >= 7:
                    secret_name = parts[6]
                    if len(parts) > 7:
                        secret_name += f"-{parts[7]}"
                    console.print(f"{name} → Secrets Manager: {secret_name}", style="magenta")
                else:
                    console.print(f"{name} → Secrets Manager: {value_from}", style="magenta")
            elif "ssm" in value_from or "parameter" in value_from:
                if ":parameter/" in value_from:
                    param_name = value_from.split(":parameter/", 1)[1]
                    console.print(f"{name} → Parameter Store: {param_name}", style="magenta")
                else:
                    console.print(f"{name} → Parameter Store: {value_from}", style="magenta")
            else:
                console.print(f"{name} → {value_from}", style="magenta")

        console.print("=" * 60, style="dim")
        console.print(f"🔒 Total: {len(secrets)} secrets configured", style="magenta")

    def show_container_port_mappings(self, cluster_name: str, task_arn: str, container_name: str) -> None:
        """Display port mappings for a container."""
        port_mappings = self.ecs_service.get_container_port_mappings(cluster_name, task_arn, container_name)

        if port_mappings is None:
            console.print(f"❌ Could not find port mappings for container '{container_name}'", style="red")
            return

        if not port_mappings:
            console.print(f"🔌 No port mappings configured for container '{container_name}'", style="yellow")
            return

        console.print(f"\n🔌 Port mappings for container '{container_name}':", style="bold blue")
        console.print("=" * 60, style="dim")

        for mapping in port_mappings:
            container_port = mapping.get("containerPort", "unknown")
            host_port = mapping.get("hostPort", "dynamic")
            protocol = mapping.get("protocol", "tcp").upper()

            host_display = host_port if host_port != 0 else "dynamic"
            console.print(f"Container:{container_port} → Host:{host_display} ({protocol})", style="blue")

        console.print("=" * 60, style="dim")
        console.print(f"🔗 Total: {len(port_mappings)} port mappings configured", style="blue")


def _build_task_feature_choices(containers: list[dict[str, Any]]) -> list[str]:
    """Build feature menu choices for containers plus exit option."""
    actions = [
        "Show tail of logs for container: {name}",
        "Show environment variables for container: {name}",
        "Show secrets for container: {name}",
        "Show port mappings for container: {name}",
    ]

    choices = [action.format(name=container["name"]) for container in containers for action in actions]
    choices.append("Exit")
    return choices
