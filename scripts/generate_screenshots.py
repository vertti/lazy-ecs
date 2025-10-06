#!/usr/bin/env python3
"""Generate feature screenshots for README documentation."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import Mock

from rich.console import Console
from rich.terminal_theme import DIMMED_MONOKAI

from lazy_ecs.features.task.comparison import compare_task_definitions
from lazy_ecs.features.task.ui import TaskUI

SVG_FORMAT_NO_CHROME = (
    '<svg class="rich-terminal" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">\n'
    "    <style>\n"
    "    @font-face {{\n"
    '        font-family: "Fira Code";\n'
    '        src: local("FiraCode-Regular"),\n'
    '                url("https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff2/'
    'FiraCode-Regular.woff2") format("woff2"),\n'
    '                url("https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff/'
    'FiraCode-Regular.woff") format("woff");\n'
    "        font-style: normal;\n"
    "        font-weight: 400;\n"
    "    }}\n"
    "    @font-face {{\n"
    '        font-family: "Fira Code";\n'
    '        src: local("FiraCode-Bold"),\n'
    '                url("https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff2/'
    'FiraCode-Bold.woff2") format("woff2"),\n'
    '                url("https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff/'
    'FiraCode-Bold.woff") format("woff");\n'
    "        font-style: bold;\n"
    "        font-weight: 700;\n"
    "    }}\n\n"
    "    .{unique_id}-matrix {{\n"
    "        font-family: Fira Code, monospace;\n"
    "        font-size: {char_height}px;\n"
    "        line-height: {line_height}px;\n"
    "        font-variant-east-asian: full-width;\n"
    "    }}\n\n"
    "    {styles}\n"
    "    </style>\n\n"
    "    <defs>\n"
    '    <clipPath id="{unique_id}-clip-terminal">\n'
    '      <rect x="0" y="0" width="{terminal_width}" height="{terminal_height}" />\n'
    "    </clipPath>\n"
    "    {lines}\n"
    "    </defs>\n\n"
    '    <rect fill="#191919" stroke="rgba(255,255,255,0.15)" stroke-width="1" '
    'x="0" y="0" width="{width}" height="{height}" rx="8"/>\n\n'
    '    <g transform="translate(12, 6)" clip-path="url(#{unique_id}-clip-terminal)">\n'
    "    {backgrounds}\n"
    '    <g class="{unique_id}-matrix">\n'
    "    {matrix}\n"
    "    </g>\n"
    "    </g>\n"
    "</svg>\n"
)


def generate_task_comparison_screenshot() -> None:
    console = Console(record=True, width=100)

    source = {
        "family": "my-app",
        "revision": 247,
        "containers": [
            {
                "name": "web",
                "image": "myapp:v1.2.3",
                "environment": {"ENV": "staging", "DEBUG": "true"},
                "cpu": 256,
                "memory": 512,
            },
        ],
        "taskCpu": "256",
        "taskMemory": "512",
    }

    target = {
        "family": "my-app",
        "revision": 238,
        "containers": [
            {
                "name": "web",
                "image": "myapp:v1.2.4",
                "environment": {"ENV": "production", "LOG_LEVEL": "info"},
                "cpu": 256,
                "memory": 512,
            },
        ],
        "taskCpu": "512",
        "taskMemory": "1024",
    }

    changes = compare_task_definitions(source, target)

    # Temporarily replace the module console
    import lazy_ecs.features.task.ui as task_ui_module

    original_console = task_ui_module.console
    task_ui_module.console = console

    mock_task_service = Mock()
    task_ui = TaskUI(mock_task_service)
    task_ui._display_comparison_results(source, target, changes)

    task_ui_module.console = original_console

    save_screenshot(console, "task-comparison")


def generate_service_status_screenshot() -> None:
    from lazy_ecs.core.utils import determine_service_status

    console = Console(record=True, width=100)

    services: list[dict[str, Any]] = [
        {"name": "api-service", "running": 3, "desired": 3, "pending": 0},
        {"name": "worker-service", "running": 5, "desired": 5, "pending": 0},
        {"name": "background-jobs", "running": 2, "desired": 3, "pending": 0},
        {"name": "legacy-app", "running": 0, "desired": 2, "pending": 0},
    ]

    console.print("Services in cluster 'production':", style="bold cyan")
    console.print()

    for svc in services:
        running: int = svc["running"]  # type: ignore
        desired: int = svc["desired"]  # type: ignore
        pending: int = svc["pending"]  # type: ignore
        icon, _ = determine_service_status(running, desired, pending)
        display = f"{icon} {svc['name']} ({svc['running']}/{svc['desired']})"
        if icon == "✅":
            console.print(display, style="green")
        elif icon == "⚠️":
            console.print(display, style="yellow")
        else:
            console.print(display, style="red")

    save_screenshot(console, "service-status")


def generate_task_failure_screenshot() -> None:
    from datetime import datetime

    from lazy_ecs.core.types import TaskHistoryDetails

    console = Console(record=True, width=100)

    mock_task_service = Mock()

    task_history: list[TaskHistoryDetails] = [
        {
            "task_arn": "arn:aws:ecs:us-east-1:123:task/prod/abc123def456789",
            "task_definition_name": "my-app",
            "task_definition_revision": "247",
            "last_status": "RUNNING",
            "desired_status": "RUNNING",
            "stop_code": None,
            "stopped_reason": None,
            "created_at": datetime(2025, 1, 15, 14, 23),
            "started_at": datetime(2025, 1, 15, 14, 23),
            "stopped_at": None,
            "containers": [],
        },
        {
            "task_arn": "arn:aws:ecs:us-east-1:123:task/prod/def456abc789012",
            "task_definition_name": "my-app",
            "task_definition_revision": "246",
            "last_status": "STOPPED",
            "desired_status": "STOPPED",
            "stop_code": None,
            "stopped_reason": None,
            "created_at": datetime(2025, 1, 15, 14, 15),
            "started_at": datetime(2025, 1, 15, 14, 15),
            "stopped_at": datetime(2025, 1, 15, 14, 16),
            "containers": [
                {
                    "name": "web",
                    "exit_code": 137,
                    "reason": "OutOfMemoryError: Java heap space",
                    "health_status": None,
                    "last_status": "STOPPED",
                },
            ],
        },
        {
            "task_arn": "arn:aws:ecs:us-east-1:123:task/prod/ghi789jkl012345",
            "task_definition_name": "my-app",
            "task_definition_revision": "245",
            "last_status": "STOPPED",
            "desired_status": "STOPPED",
            "stop_code": "TaskFailedToStart",
            "stopped_reason": "CannotPullContainerError: image not found",
            "created_at": datetime(2025, 1, 15, 14, 10),
            "started_at": None,
            "stopped_at": datetime(2025, 1, 15, 14, 10),
            "containers": [],
        },
    ]

    mock_task_service.get_task_failure_analysis.side_effect = [
        "✅ Task is currently running",
        "🔴 Container 'web' killed due to out...",
        "📦 Failed to pull container image - ...",
    ]

    import lazy_ecs.features.task.ui as task_ui_module

    original_console = task_ui_module.console
    task_ui_module.console = console

    task_ui = TaskUI(mock_task_service)

    console.print("Task History for service 'api-service'", style="bold cyan")
    console.print("=" * 80, style="dim")

    table = task_ui._create_history_table()
    for task in task_history:
        table.add_row(*task_ui._format_task_row(task))

    console.print(table)
    task_ui._display_history_summary(task_history)

    task_ui_module.console = original_console

    save_screenshot(console, "task-history")


def generate_metrics_screenshot() -> None:
    from lazy_ecs.core.types import ServiceMetrics
    from lazy_ecs.features.service.ui import ServiceUI

    console = Console(record=True, width=100)

    metrics: ServiceMetrics = {
        "cpu": {"current": 23.5, "average": 21.2, "maximum": 45.8, "minimum": 12.1},
        "memory": {"current": 67.3, "average": 65.1, "maximum": 78.4, "minimum": 58.2},
    }

    import lazy_ecs.features.service.ui as service_ui_module

    original_console = service_ui_module.console
    service_ui_module.console = console

    mock_service_service = Mock()
    mock_service_actions = Mock()
    service_ui = ServiceUI(mock_service_service, mock_service_actions)

    service_ui.display_service_metrics("api-service", metrics)

    service_ui_module.console = original_console

    save_screenshot(console, "metrics")


def save_screenshot(console: Console, name: str) -> None:
    """Save console output as SVG."""
    output_dir = Path(__file__).parent.parent / "images"
    output_dir.mkdir(exist_ok=True)

    output_path = output_dir / f"{name}.svg"
    console.save_svg(str(output_path), title="", theme=DIMMED_MONOKAI, code_format=SVG_FORMAT_NO_CHROME)
    print(f"✅ Generated {output_path}")


def main() -> None:
    """Generate all screenshots."""
    print("Generating feature screenshots...\n")

    generate_task_comparison_screenshot()
    generate_service_status_screenshot()
    generate_task_failure_screenshot()
    generate_metrics_screenshot()

    print("\n✅ All screenshots generated in images/")


if __name__ == "__main__":
    main()
