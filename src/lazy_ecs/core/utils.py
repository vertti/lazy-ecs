"""Utility functions for lazy-ecs."""

from __future__ import annotations

import atexit
import select
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from typing import TYPE_CHECKING, Literal

from rich.console import Console
from rich.spinner import Spinner

# Try to import Unix-specific terminal control modules
try:
    import termios
    import tty

    HAS_TERMIOS = True
    # Store original terminal settings globally
    _original_terminal_settings = None
    if sys.stdin.isatty():
        _original_terminal_settings = termios.tcgetattr(sys.stdin.fileno())

        # Register cleanup on exit
        def restore_terminal() -> None:
            if _original_terminal_settings and sys.stdin.isatty():
                with suppress(Exception):
                    termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, _original_terminal_settings)

        atexit.register(restore_terminal)
except ImportError:
    HAS_TERMIOS = False

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


def wait_for_keypress(stop_event: threading.Event) -> str | None:
    """Wait for a single keypress in a non-blocking manner.

    Returns the key pressed, or None if stop_event is set.
    This runs in a separate thread to allow checking for keypresses without blocking.
    """
    if HAS_TERMIOS and sys.stdin.isatty():
        # Unix/Linux/macOS with terminal support
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            # Set terminal to cbreak mode for single-character input
            tty.setcbreak(fd)

            # Check for input with timeout
            while not stop_event.is_set():
                # Use select to check if input is available (0.01 second timeout for responsiveness)
                if select.select([sys.stdin], [], [], 0.01)[0]:
                    char = sys.stdin.read(1)
                    # Handle Ctrl-C properly
                    if char == "\x03":  # Ctrl-C
                        raise KeyboardInterrupt()
                    return char

            return None
        except (Exception, KeyboardInterrupt):
            # Restore settings before re-raising
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            if isinstance(sys.exc_info()[1], KeyboardInterrupt):
                raise
            return None
        finally:
            # Always restore terminal settings
            with suppress(Exception):
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    else:
        # Fallback for Windows or when termios is not available
        try:
            return sys.stdin.read(1)
        except Exception:
            return None
