"""Navigation utilities for UI components."""

from __future__ import annotations

import questionary
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.keys import Keys
from rich.console import Console

PAGINATION_THRESHOLD = 30


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


def add_navigation_choices_with_shortcuts(choices: list[dict[str, str]], back_text: str | None) -> list:
    """Add navigation choices with shortcut keys to existing choices list."""
    nav_choices = []

    # Add original choices
    for choice in choices:
        nav_choices.append(questionary.Choice(choice["name"], choice["value"]))

    # Add back choice with 'b' shortcut only if back_text is provided
    if back_text:
        nav_choices.append(questionary.Choice(f"⬅️ {back_text} (b)", "navigation:back", shortcut_key="b"))

    # Add exit choice with 'q' shortcut
    nav_choices.append(questionary.Choice("❌ Exit (q)", "navigation:exit", shortcut_key="q"))

    return nav_choices


def select_with_navigation(prompt: str, choices: list[dict[str, str]], back_text: str | None) -> str | None:
    """Standard selection with back/exit navigation and ESC key support."""
    # Use the shortcut version for 'b' and 'q' keys
    nav_choices = add_navigation_choices_with_shortcuts(choices, back_text)

    # Create a questionary select question
    question = questionary.select(prompt, choices=nav_choices, style=get_questionary_style(), use_shortcuts=True)

    # Add ESC key binding by accessing the underlying application
    if hasattr(question, "application"):
        # Add custom key binding for ESC key
        custom_bindings = KeyBindings()

        @custom_bindings.add(Keys.Escape, eager=True)
        def _(event: KeyPressEvent) -> None:
            """Handle ESC key press by simulating 'b' + Enter key sequence."""
            # Feed 'b' and Enter to the key processor without calling process_keys
            from prompt_toolkit.key_binding.key_processor import KeyPress

            # Feed both 'b' and Enter keys to the input queue
            b_key = KeyPress("b", "")
            enter_key = KeyPress(Keys.ControlM, "")  # Enter key
            event.app.key_processor.feed(b_key)
            event.app.key_processor.feed(enter_key)

        # Get the existing bindings and merge them
        if hasattr(question.application, "key_bindings") and question.application.key_bindings:
            # Create a new key bindings object that includes both
            merged_bindings = KeyBindings()

            # Add existing bindings
            for binding in question.application.key_bindings.bindings:
                merged_bindings.bindings.append(binding)

            # Add our custom ESC binding
            for binding in custom_bindings.bindings:
                merged_bindings.bindings.append(binding)

            question.application.key_bindings = merged_bindings

    return question.ask()


def select_with_pagination(
    prompt: str, choices: list[dict[str, str]], back_text: str | None, page_size: int = 25
) -> str | None:
    """Selection with pagination for large lists."""
    total_items = len(choices)
    total_pages = (total_items + page_size - 1) // page_size
    current_page = 0

    while True:
        start_idx = current_page * page_size
        end_idx = min(start_idx + page_size, total_items)
        page_choices = choices[start_idx:end_idx]

        page_prompt = f"{prompt} (Page {current_page + 1} of {total_pages})"

        paginated_choices = []
        for choice in page_choices:
            paginated_choices.append(questionary.Choice(choice["name"], choice["value"]))

        if current_page < total_pages - 1:
            paginated_choices.append(
                questionary.Choice(
                    f"→ Next Page ({end_idx + 1}-{min(end_idx + page_size, total_items)})", "pagination:next"
                )
            )

        if current_page > 0:
            paginated_choices.append(
                questionary.Choice(f"← Previous Page ({start_idx - page_size + 1}-{start_idx})", "pagination:previous")
            )

        if back_text:
            paginated_choices.append(questionary.Choice(f"⬅️ {back_text}", "navigation:back"))

        paginated_choices.append(questionary.Choice("❌ Exit", "navigation:exit"))

        selected = questionary.select(
            page_prompt, choices=paginated_choices, style=get_questionary_style(), use_shortcuts=False
        ).ask()

        if selected == "pagination:next":
            current_page += 1
        elif selected == "pagination:previous":
            current_page -= 1
        else:
            return selected


def select_with_auto_pagination(
    prompt: str, choices: list[dict[str, str]], back_text: str | None, threshold: int = PAGINATION_THRESHOLD
) -> str | None:
    """Select with automatic pagination based on choice count.

    Uses keyboard shortcuts for small lists (≤threshold), pagination for large lists (>threshold).
    """
    select_fn = select_with_pagination if len(choices) > threshold else select_with_navigation
    return select_fn(prompt, choices, back_text)
