"""UI components for container operations."""

from __future__ import annotations

from datetime import datetime

from rich.console import Console

from ...core.base import BaseUIComponent
from ...core.utils import print_error
from .container import ContainerService

console = Console()


class ContainerUI(BaseUIComponent):
    """UI component for container display."""

    def __init__(self, container_service: ContainerService) -> None:
        super().__init__()
        self.container_service = container_service

    def show_container_logs(self, cluster_name: str, task_arn: str, container_name: str, lines: int = 50) -> None:
        """Display the last N lines of logs for a container."""
        log_config = self.container_service.get_log_config(cluster_name, task_arn, container_name)
        if not log_config:
            print_error(f"Could not find log configuration for container '{container_name}'")
            console.print("Available log groups:", style="dim")
            log_groups = self.container_service.list_log_groups(cluster_name, container_name)
            for group in log_groups:
                console.print(f"  • {group}", style="cyan")
            return

        log_group_name = log_config["log_group"]
        log_stream_name = log_config["log_stream"]

        events = self.container_service.get_container_logs(log_group_name, log_stream_name, lines)

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
        context = self.container_service.get_container_context(cluster_name, task_arn, container_name)
        if not context:
            print_error(f"Could not find container '{container_name}'")
            return

        env_vars = self.container_service.get_environment_variables(context)

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
        context = self.container_service.get_container_context(cluster_name, task_arn, container_name)
        if not context:
            print_error(f"Could not find container '{container_name}'")
            return

        secrets = self.container_service.get_secrets(context)

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
        context = self.container_service.get_container_context(cluster_name, task_arn, container_name)
        if not context:
            print_error(f"Could not find container '{container_name}'")
            return

        port_mappings = self.container_service.get_port_mappings(context)

        if not port_mappings:
            console.print(f"🌐 No port mappings configured for container '{container_name}'", style="yellow")
            return

        console.print(f"\n🌐 Port mappings for container '{container_name}':", style="bold cyan")
        console.print("=" * 50, style="dim")

        for mapping in port_mappings:
            container_port = mapping.get("containerPort", "N/A")
            host_port = mapping.get("hostPort", "dynamic")
            protocol = mapping.get("protocol", "tcp")
            console.print(f"Container: {container_port} → Host: {host_port} ({protocol})", style="white")

        console.print("=" * 50, style="dim")
        console.print(f"🔗 Total: {len(port_mappings)} port mappings", style="blue")

    def show_container_volume_mounts(self, cluster_name: str, task_arn: str, container_name: str) -> None:
        """Display volume mounts for a container."""
        context = self.container_service.get_container_context(cluster_name, task_arn, container_name)
        if not context:
            print_error(f"Could not find container '{container_name}'")
            return

        volume_mounts = self.container_service.get_volume_mounts(context)

        if not volume_mounts:
            console.print(f"💾 No volume mounts configured for container '{container_name}'", style="yellow")
            return

        console.print(f"\n💾 Volume mounts for container '{container_name}':", style="bold cyan")
        console.print("=" * 70, style="dim")

        for mount in volume_mounts:
            source = mount["source_volume"]
            dest = mount["container_path"]
            readonly = "RO" if mount["read_only"] else "RW"
            host_path = mount["host_path"] or "N/A"

            console.print(f"Volume: {source} → {dest} ({readonly})", style="white")
            console.print(f"  Host path: {host_path}", style="dim")

        console.print("=" * 70, style="dim")
        console.print(f"📂 Total: {len(volume_mounts)} volume mounts", style="blue")
