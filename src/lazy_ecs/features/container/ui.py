"""UI components for container operations."""

from __future__ import annotations

import queue
import threading
import time
from contextlib import suppress
from typing import Any, cast

from rich.console import Console

from ...core.base import BaseUIComponent
from ...core.utils import print_error, show_spinner, wait_for_keypress
from .container import ContainerService
from .models import Action, LogEvent

console = Console()

SEPARATOR_WIDTH = 80
LOG_POLL_INTERVAL = 0.01  # seconds


class ContainerUI(BaseUIComponent):
    """UI component for container display."""

    def __init__(self, container_service: ContainerService) -> None:
        super().__init__()
        self.container_service = container_service

    @staticmethod
    def _drain_queue(q: queue.Queue[Any]) -> None:
        """Drain all items from a queue without blocking."""
        while not q.empty():
            try:
                q.get_nowait()
            except queue.Empty:
                break

    def show_logs_live_tail(self, cluster_name: str, task_arn: str, container_name: str, lines: int = 50) -> None:
        """Display recent logs then continue streaming in real time for a container with interactive filtering."""
        log_config = self.container_service.get_log_config(cluster_name, task_arn, container_name)
        if not log_config:
            print_error(f"Could not find log configuration for container '{container_name}'")
            console.print("Available log groups:", style="dim")
            log_groups = self.container_service.list_log_groups(cluster_name, container_name)
            for group in log_groups:
                console.print(f"  • {group}", style="cyan")
            return

        log_group_name = log_config.get("log_group")
        log_stream_name = log_config.get("log_stream")

        filter_pattern = ""
        while True:
            action = self._display_logs_with_tail(
                container_name, log_group_name, log_stream_name, filter_pattern, lines
            )

            if action == Action.STOP:
                console.print("\nStopped tailing logs.", style="yellow")
                break
            if action == Action.FILTER:
                console.print("\n" + "=" * SEPARATOR_WIDTH, style="dim")
                console.print("🔍 FILTER MODE - Enter CloudWatch filter pattern", style="bold cyan")
                console.print("Examples:", style="dim")
                console.print("  ERROR               - Include only ERROR messages", style="dim")
                console.print("  -healthcheck        - Exclude healthcheck messages", style="dim")
                console.print("  -session -determine - Exclude both session and determine", style="dim")
                console.print("  ERROR -healthcheck  - Include ERROR, exclude healthcheck", style="dim")
                new_filter = console.input("Filter pattern → ").strip()
                if new_filter:
                    filter_pattern = new_filter
                    console.print(f"✓ Filter applied: {filter_pattern}", style="green")
            elif action == Action.CLEAR:
                filter_pattern = ""
                console.print("\n✓ Filter cleared", style="green")

    def _display_logs_with_tail(
        self,
        container_name: str,
        log_group_name: str,
        log_stream_name: str,
        filter_pattern: str,
        lines: int,
    ) -> Action | None:
        """Display historical logs then tail new logs with optional filtering.

        Returns the action taken by the user.
        """
        # Show filter status
        if filter_pattern:
            console.print(f"\n🔍 Active filter: {filter_pattern}", style="yellow")

        # Fetch and display recent logs
        if filter_pattern:
            events = self.container_service.get_container_logs_filtered(
                log_group_name, log_stream_name, filter_pattern, lines
            )
        else:
            events = self.container_service.get_container_logs(log_group_name, log_stream_name, lines)

        console.print(f"\nLast {len(events)} log entries for container '{container_name}':", style="bold cyan")
        console.print(f"Log group: {log_group_name}", style="dim")
        console.print(f"Log stream: {log_stream_name}", style="dim")
        console.print("=" * SEPARATOR_WIDTH, style="dim")

        seen_logs = set()
        for event in events:
            event_id = event.get("eventId")
            log_event = LogEvent(
                timestamp=event["timestamp"],
                message=event["message"].rstrip(),
                event_id=event_id if isinstance(event_id, str) else None,
            )
            console.print(log_event.format())
            seen_logs.add(log_event.key)

        # Tail new logs with keyboard commands
        console.print("\nTailing logs... Press: (s)top  (f)ilter  (c)lear filter", style="bold cyan")
        console.print("=" * SEPARATOR_WIDTH, style="dim")

        stop_event = threading.Event()
        key_queue: queue.Queue[str | None] = queue.Queue()
        log_queue: queue.Queue[dict[str, Any] | None] = queue.Queue()

        def keyboard_listener() -> None:
            while not stop_event.is_set():
                try:
                    key = wait_for_keypress(stop_event)
                    if key:
                        key_queue.put(key)
                except KeyboardInterrupt:
                    key_queue.put(None)  # Signal interrupt
                    raise

        def log_reader() -> None:
            """Read logs in separate thread to avoid blocking."""
            log_generator = None
            try:
                log_generator = self.container_service.get_live_container_logs_tail(
                    log_group_name, log_stream_name, filter_pattern
                )
                for event in log_generator:
                    if stop_event.is_set():
                        break
                    log_queue.put(cast(dict[str, Any], event))
            except Exception:
                pass  # Iterator exhausted or error
            finally:
                # Ensure generator is properly closed
                if log_generator and hasattr(log_generator, "close"):
                    with suppress(Exception):
                        log_generator.close()
                log_queue.put(None)  # Signal end of logs

        keyboard_thread = threading.Thread(target=keyboard_listener, daemon=True)
        keyboard_thread.start()

        log_thread = threading.Thread(target=log_reader, daemon=True)
        log_thread.start()

        action = None

        try:
            while True:
                # Check for keyboard input first (more responsive)
                try:
                    key = key_queue.get_nowait()
                    if key:
                        action = Action.from_key(key)
                        if action:
                            stop_event.set()
                            self._drain_queue(key_queue)
                            # Give immediate feedback
                            if action == Action.FILTER:
                                console.print("\n[Entering filter mode...]", style="cyan")
                            elif action == Action.CLEAR:
                                console.print("\n[Clearing filter...]", style="green")
                            break
                except queue.Empty:
                    pass

                # Check for new log events (non-blocking)
                try:
                    event = log_queue.get_nowait()
                    if event is None:
                        # End of logs signal
                        pass
                    else:
                        event_id = event.get("eventId")
                        log_event = LogEvent(
                            timestamp=event.get("timestamp"),
                            message=str(event.get("message", "")).rstrip(),
                            event_id=event_id if isinstance(event_id, str) else None,
                        )
                        if log_event.key not in seen_logs:
                            seen_logs.add(log_event.key)
                            console.print(log_event.format())
                except queue.Empty:
                    # No new logs, just wait a bit
                    time.sleep(LOG_POLL_INTERVAL)  # Small delay to avoid busy-waiting
        except KeyboardInterrupt:
            console.print("\n🛑 Interrupted.", style="yellow")
            action = Action.STOP
        finally:
            stop_event.set()

        return action

    def show_container_environment_variables(self, cluster_name: str, task_arn: str, container_name: str) -> None:
        with show_spinner():
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
        with show_spinner():
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
        with show_spinner():
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
        with show_spinner():
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
