"""Navigation utilities for UI components."""

from __future__ import annotations

import questionary
from rich.console import Console


def parse_selection(selected: str | None) -> tuple[str, str, str]:
    """Parse selection into (type, value, extra). Returns ('unknown', selected, '') if no colon."""
    if not selected or ":" not in selected:
        return ("unknown", selected or "", "")

    parts = selected.split(":", 2)
    if len(parts) == 3:
        return (parts[0], parts[1], parts[2])  # container_action:show_logs:web
    return (parts[0], parts[1], "")  # task:arn or navigation:back


def handle_navigation(selected: str | None) -> tuple[bool, bool]:
    """Handle navigation. Returns (should_continue, should_exit)."""
    console = Console()
    if not selected:
        console.print("\n👋 Goodbye!", style="cyan")
        return False, True

    selection_type, value, _ = parse_selection(selected)
    if selection_type == "navigation":
        if value == "exit":
            console.print("\n👋 Goodbye!", style="cyan")
            return False, True
        if value == "back":
            return False, False

    return True, False


def get_questionary_style() -> questionary.Style:
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


def add_navigation_choices(choices: list[dict[str, str]], back_text: str) -> list[dict[str, str]]:
    """Add navigation choices to existing choices list and return new list."""
    return [
        *choices,
        {"name": f"⬅️ {back_text}", "value": "navigation:back"},
        {"name": "❌ Exit", "value": "navigation:exit"},
    ]


def select_with_navigation(prompt: str, choices: list[dict[str, str]], back_text: str) -> str | None:
    """Standard selection with back/exit navigation."""
    nav_choices = add_navigation_choices(choices, back_text)
    return questionary.select(prompt, choices=nav_choices, style=get_questionary_style()).ask()
