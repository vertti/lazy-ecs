"""Tests for core navigation functions."""

from unittest.mock import patch

from lazy_ecs.core.navigation import (
    add_navigation_choices,
    add_navigation_choices_with_shortcuts,
    get_questionary_style,
    handle_navigation,
    parse_selection,
    select_with_navigation,
    select_with_pagination,
)


def test_parse_selection_with_container_action():
    """Test parsing container action selection with three parts."""
    result = parse_selection("container_action:tail_logs:web")
    assert result == ("container_action", "tail_logs", "web")


def test_parse_selection_with_two_parts():
    """Test parsing selection with two parts."""
    result = parse_selection("navigation:back")
    assert result == ("navigation", "back", "")


def test_parse_selection_with_no_colon():
    """Test parsing selection without colon."""
    result = parse_selection("simple_value")
    assert result == ("unknown", "simple_value", "")


def test_parse_selection_with_none():
    """Test parsing None selection."""
    result = parse_selection(None)
    assert result == ("unknown", "", "")


def test_handle_navigation_back():
    """Test navigation handling for back action."""
    should_continue, should_exit = handle_navigation("navigation:back")
    assert not should_continue
    assert not should_exit


def test_handle_navigation_exit():
    """Test navigation handling for exit action."""
    should_continue, should_exit = handle_navigation("navigation:exit")
    assert not should_continue
    assert should_exit


def test_handle_navigation_none_selection():
    """Test navigation handling for None selection (exit)."""
    should_continue, should_exit = handle_navigation(None)
    assert not should_continue
    assert should_exit


def test_handle_navigation_continue():
    """Test navigation handling for non-navigation selection."""
    should_continue, should_exit = handle_navigation("service:web-api")
    assert should_continue
    assert not should_exit


def test_add_navigation_choices():
    """Test adding navigation choices to existing choices."""
    choices = [{"name": "Option 1", "value": "opt1"}]
    result = add_navigation_choices(choices, "Back to services")

    assert len(result) == 3
    assert result[0] == {"name": "Option 1", "value": "opt1"}
    assert result[1] == {"name": "⬅️ Back to services", "value": "navigation:back"}
    assert result[2] == {"name": "❌ Exit", "value": "navigation:exit"}


def test_get_questionary_style():
    """Test questionary style configuration."""
    style = get_questionary_style()
    assert style is not None


def test_add_navigation_choices_with_shortcuts():
    """Test adding navigation choices with shortcut key support."""
    choices = [{"name": "Option 1", "value": "opt1"}]
    result = add_navigation_choices_with_shortcuts(choices, "Back to test")

    assert len(result) == 3

    # Check that we have Choice objects with shortcut keys
    import questionary

    assert isinstance(result[1], questionary.Choice)  # Back option
    assert isinstance(result[2], questionary.Choice)  # Exit option

    # Check values
    assert result[1].value == "navigation:back"
    assert result[2].value == "navigation:exit"


@patch("lazy_ecs.core.navigation.questionary.select")
def test_select_with_navigation_esc_functionality(mock_select):
    """Test select with navigation ESC functionality."""
    mock_select.return_value.ask.return_value = "navigation:back"

    choices = [{"name": "Option 1", "value": "opt1"}]
    result = select_with_navigation("Test prompt", choices, "Back")

    assert result == "navigation:back"
    mock_select.assert_called_once()

    # Verify the call was made with use_shortcuts=True
    call_kwargs = mock_select.call_args[1]
    assert call_kwargs["use_shortcuts"] is True

    # Verify choices are Choice objects (not dicts)
    choices_passed = call_kwargs["choices"]
    import questionary

    assert all(isinstance(choice, questionary.Choice) for choice in choices_passed)


@patch("lazy_ecs.core.navigation.questionary.select")
def test_select_with_navigation_choices_expanded(mock_select):
    """Test that select_with_navigation properly expands choices."""
    mock_select.return_value.ask.return_value = "opt1"

    choices = [{"name": "Option 1", "value": "opt1"}]
    select_with_navigation("Test prompt", choices, "Back to test")

    # Verify the call was made with expanded choices
    call_args = mock_select.call_args
    passed_choices = call_args[1]["choices"]

    assert len(passed_choices) == 3
    # Check that choices are Choice objects with correct values
    assert passed_choices[0].value == "opt1"
    assert passed_choices[1].value == "navigation:back"
    assert passed_choices[2].value == "navigation:exit"


@patch("lazy_ecs.core.navigation.questionary.select")
def test_select_with_pagination_single_page(mock_select):
    mock_select.return_value.ask.return_value = "item-5"

    choices = [{"name": f"Item {i}", "value": f"item-{i}"} for i in range(20)]
    result = select_with_pagination("Select item:", choices, "Back", page_size=25)

    assert result == "item-5"
    mock_select.assert_called_once()
    call_kwargs = mock_select.call_args[1]
    assert call_kwargs["use_shortcuts"] is False


@patch("lazy_ecs.core.navigation.questionary.select")
def test_select_with_pagination_navigation_between_pages(mock_select):
    mock_select.return_value.ask.side_effect = ["pagination:next", "item-35"]

    choices = [{"name": f"Item {i}", "value": f"item-{i}"} for i in range(50)]
    result = select_with_pagination("Select item:", choices, "Back", page_size=25)

    assert result == "item-35"
    assert mock_select.call_count == 2


@patch("lazy_ecs.core.navigation.questionary.select")
def test_select_with_pagination_back_from_second_page(mock_select):
    mock_select.return_value.ask.side_effect = ["pagination:next", "navigation:back"]

    choices = [{"name": f"Item {i}", "value": f"item-{i}"} for i in range(50)]
    result = select_with_pagination("Select item:", choices, "Back", page_size=25)

    assert result == "navigation:back"
    assert mock_select.call_count == 2


@patch("lazy_ecs.core.navigation.questionary.select")
def test_select_with_pagination_previous_page(mock_select):
    mock_select.return_value.ask.side_effect = ["pagination:next", "pagination:previous", "item-5"]

    choices = [{"name": f"Item {i}", "value": f"item-{i}"} for i in range(50)]
    result = select_with_pagination("Select item:", choices, "Back", page_size=25)

    assert result == "item-5"
    assert mock_select.call_count == 3


@patch("lazy_ecs.core.navigation.questionary.select")
def test_select_with_pagination_exit(mock_select):
    mock_select.return_value.ask.return_value = "navigation:exit"

    choices = [{"name": f"Item {i}", "value": f"item-{i}"} for i in range(50)]
    result = select_with_pagination("Select item:", choices, "Back", page_size=25)

    assert result == "navigation:exit"
