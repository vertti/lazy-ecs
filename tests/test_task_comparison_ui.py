"""Tests for task comparison UI."""

from unittest.mock import Mock, patch

from lazy_ecs.features.task.ui import TaskUI


@patch("lazy_ecs.features.task.ui.console")
def test_show_task_definition_comparison_no_service(_mock_console):
    task_ui = TaskUI(Mock(), None)
    task_details = {
        "task_arn": "arn:task",
        "task_definition_name": "web",
        "task_definition_revision": "5",
    }

    task_ui.show_task_definition_comparison(task_details)  # type: ignore[arg-type]


@patch("lazy_ecs.features.task.ui.console")
@patch("lazy_ecs.features.task.ui.print_warning")
def test_show_task_definition_comparison_not_enough_revisions(_mock_warning, _mock_console):
    mock_comparison_service = Mock()
    mock_comparison_service.list_task_definition_revisions.return_value = [{"revision": 1, "arn": "arn:1"}]
    task_ui = TaskUI(Mock(), mock_comparison_service)
    task_details = {
        "task_arn": "arn:task",
        "task_definition_name": "web",
        "task_definition_revision": "1",
    }

    task_ui.show_task_definition_comparison(task_details)  # type: ignore[arg-type]


@patch("lazy_ecs.features.task.ui.select_with_auto_pagination")
@patch("lazy_ecs.features.task.ui.console")
def test_show_task_definition_comparison_user_cancels(_mock_console, mock_select):
    mock_comparison_service = Mock()
    mock_comparison_service.list_task_definition_revisions.return_value = [
        {"revision": 5, "arn": "arn:5"},
        {"revision": 4, "arn": "arn:4"},
    ]
    mock_select.return_value = None
    task_ui = TaskUI(Mock(), mock_comparison_service)
    task_details = {
        "task_arn": "arn:task",
        "task_definition_name": "web",
        "task_definition_revision": "5",
    }

    task_ui.show_task_definition_comparison(task_details)  # type: ignore[arg-type]

    mock_select.assert_called_once()


@patch("lazy_ecs.features.task.ui.compare_task_definitions")
@patch("lazy_ecs.features.task.ui.select_with_auto_pagination")
@patch("lazy_ecs.features.task.ui.console")
def test_show_task_definition_comparison_success(_mock_console, mock_select, mock_compare):
    mock_comparison_service = Mock()
    mock_comparison_service.list_task_definition_revisions.return_value = [
        {"revision": 5, "arn": "arn:5"},
        {"revision": 4, "arn": "arn:4"},
    ]
    source_def = {"family": "web", "revision": 5}
    target_def = {"family": "web", "revision": 4}
    mock_comparison_service.get_task_definitions_for_comparison.return_value = (source_def, target_def)
    mock_compare.return_value = [{"type": "image_changed", "old": "nginx:1.0", "new": "nginx:2.0"}]
    mock_select.return_value = "arn:4"

    task_ui = TaskUI(Mock(), mock_comparison_service)
    task_ui._display_comparison_results = Mock()
    task_details = {
        "task_arn": "arn:task",
        "task_definition_name": "web",
        "task_definition_revision": "5",
    }

    task_ui.show_task_definition_comparison(task_details)  # type: ignore[arg-type]

    task_ui._display_comparison_results.assert_called_once()


@patch("lazy_ecs.features.task.ui.console")
def test_display_comparison_results_no_changes(_mock_console):
    task_ui = TaskUI(Mock())

    task_ui._display_comparison_results(
        {"family": "web", "revision": 5},
        {"family": "web", "revision": 4},
        [],
    )


@patch("lazy_ecs.features.task.ui.console")
def test_display_comparison_results_with_changes(_mock_console):
    task_ui = TaskUI(Mock())
    task_ui._display_change = Mock()
    changes = [
        {"type": "image_changed", "old": "nginx:1.0", "new": "nginx:2.0"},
        {"type": "cpu_changed", "old": "256", "new": "512"},
    ]

    task_ui._display_comparison_results(
        {"family": "web", "revision": 5},
        {"family": "web", "revision": 4},
        changes,
    )

    assert task_ui._display_change.call_count == 2


@patch("lazy_ecs.features.task.ui.console")
def test_display_change_environment_added(_mock_console):
    task_ui = TaskUI(Mock())
    change = {"type": "environment_added", "container": "web", "key": "DEBUG", "value": "true"}

    task_ui._display_change(change)


@patch("lazy_ecs.features.task.ui.console")
def test_display_change_environment_removed(_mock_console):
    task_ui = TaskUI(Mock())
    change = {"type": "environment_removed", "container": "web", "key": "OLD_VAR", "value": "old"}

    task_ui._display_change(change)


@patch("lazy_ecs.features.task.ui.console")
def test_display_change_environment_changed(_mock_console):
    task_ui = TaskUI(Mock())
    change = {"type": "environment_changed", "container": "web", "key": "PORT", "old": "8080", "new": "3000"}

    task_ui._display_change(change)


@patch("lazy_ecs.features.task.ui.console")
def test_display_change_secret_changed(_mock_console):
    task_ui = TaskUI(Mock())
    change = {"type": "secret_changed", "container": "web", "key": "API_KEY", "old": "arn:1", "new": "arn:2"}

    task_ui._display_change(change)


@patch("lazy_ecs.features.task.ui.console")
def test_display_change_ports_changed(_mock_console):
    task_ui = TaskUI(Mock())
    change = {
        "type": "ports_changed",
        "container": "web",
        "old": [{"containerPort": 8080}],
        "new": [{"containerPort": 3000}],
    }

    task_ui._display_change(change)


@patch("lazy_ecs.features.task.ui.console")
def test_display_change_command_changed(_mock_console):
    task_ui = TaskUI(Mock())
    change = {
        "type": "command_changed",
        "container": "web",
        "old": ["npm", "start"],
        "new": ["node", "server.js"],
    }

    task_ui._display_change(change)


@patch("lazy_ecs.features.task.ui.console")
def test_display_change_volumes_changed(_mock_console):
    task_ui = TaskUI(Mock())
    change = {
        "type": "volumes_changed",
        "container": "web",
        "old": [{"sourceVolume": "data", "containerPath": "/data"}],
        "new": [{"sourceVolume": "logs", "containerPath": "/logs"}],
    }

    task_ui._display_change(change)


@patch("lazy_ecs.features.task.ui.console")
def test_display_change_generic(_mock_console):
    task_ui = TaskUI(Mock())
    change = {"type": "memory_changed", "old": "256", "new": "512"}

    task_ui._display_change(change)


@patch("lazy_ecs.features.task.ui.console")
def test_display_change_unknown_type_ignored(_mock_console):
    task_ui = TaskUI(Mock())
    change = {"type": "unknown_change_type"}

    task_ui._display_change(change)
