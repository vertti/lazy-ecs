"""Tests for task history UI functionality."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from lazy_ecs.core.types import TaskHistoryDetails
from lazy_ecs.features.task.ui import TaskUI


class TestTaskHistoryUI:
    """Test task history UI functionality."""

    @pytest.fixture
    def mock_task_service(self):
        """Mock task service for testing."""
        return Mock()

    @pytest.fixture
    def task_ui(self, mock_task_service):
        """Task UI instance for testing."""
        return TaskUI(mock_task_service)

    @pytest.fixture
    def sample_task_history(self):
        """Sample task history data for testing."""
        return [
            {
                "task_arn": "arn:aws:ecs:us-east-1:123456789012:task/cluster/running-task",
                "task_definition_name": "web-api",
                "task_definition_revision": "6",
                "last_status": "RUNNING",
                "desired_status": "RUNNING",
                "stop_code": None,
                "stopped_reason": None,
                "created_at": datetime(2024, 1, 15, 12, 0, 0),
                "started_at": datetime(2024, 1, 15, 12, 1, 0),
                "stopped_at": None,
                "containers": [
                    {
                        "name": "web-api",
                        "exit_code": None,
                        "reason": None,
                        "health_status": "HEALTHY",
                        "last_status": "RUNNING",
                    }
                ],
            },
            {
                "task_arn": "arn:aws:ecs:us-east-1:123456789012:task/cluster/failed-task",
                "task_definition_name": "web-api",
                "task_definition_revision": "5",
                "last_status": "STOPPED",
                "desired_status": "STOPPED",
                "stop_code": "TaskFailedToStart",
                "stopped_reason": "Essential container in task exited",
                "created_at": datetime(2024, 1, 15, 11, 30, 0),
                "started_at": datetime(2024, 1, 15, 11, 31, 0),
                "stopped_at": datetime(2024, 1, 15, 11, 35, 0),
                "containers": [
                    {
                        "name": "web-api",
                        "exit_code": 137,
                        "reason": "OutOfMemoryError: Container killed due to memory usage",
                        "health_status": "UNHEALTHY",
                        "last_status": "STOPPED",
                    }
                ],
            },
        ]

    @patch("lazy_ecs.features.task.ui.console.print")
    def test_display_task_history(self, mock_print, task_ui, mock_task_service, sample_task_history):
        """Test displaying task history."""
        mock_task_service.get_task_history.return_value = sample_task_history
        mock_task_service.get_task_failure_analysis.side_effect = [
            "✅ Task is currently running",
            "🔴 Container 'web-api' killed due to out of memory (OOM)",
        ]

        task_ui.display_task_history("test-cluster", "web-service")

        # Verify service method was called
        mock_task_service.get_task_history.assert_called_once_with("test-cluster", "web-service")

        # Verify service method was called correctly
        mock_task_service.get_task_failure_analysis.assert_called()

        # Verify title was printed
        assert any("Task History" in str(call) for call in mock_print.call_args_list)

        # The status indicators are displayed in a table, so we check that the table was created
        # The exact string matching is tricky with Rich tables, so we check the method calls
        assert len(mock_print.call_args_list) > 3  # Title, table, summary lines

    @patch("lazy_ecs.features.task.ui.print_warning")
    def test_display_task_history_empty(self, mock_print_warning, task_ui, mock_task_service):
        """Test displaying empty task history."""
        mock_task_service.get_task_history.return_value = []

        task_ui.display_task_history("test-cluster", "web-service")

        mock_task_service.get_task_history.assert_called_once_with("test-cluster", "web-service")
        mock_print_warning.assert_called_once_with("No task history found for this service")

    @patch("lazy_ecs.features.task.ui.console.print")
    def test_display_failure_analysis(self, mock_print, task_ui, mock_task_service):
        """Test displaying failure analysis for a specific task."""
        failed_task: TaskHistoryDetails = {
            "task_arn": "arn:aws:ecs:us-east-1:123456789012:task/cluster/failed-task",
            "task_definition_name": "web-api",
            "task_definition_revision": "5",
            "last_status": "STOPPED",
            "desired_status": "STOPPED",
            "stop_code": "TaskFailedToStart",
            "stopped_reason": "Essential container in task exited",
            "created_at": datetime(2024, 1, 15, 11, 30, 0),
            "started_at": datetime(2024, 1, 15, 11, 31, 0),
            "stopped_at": datetime(2024, 1, 15, 11, 35, 0),
            "containers": [
                {
                    "name": "web-api",
                    "exit_code": 137,
                    "reason": "OutOfMemoryError: Container killed due to memory usage",
                    "health_status": "UNHEALTHY",
                    "last_status": "STOPPED",
                }
            ],
        }

        mock_task_service.get_task_failure_analysis.return_value = (
            "🔴 Container 'web-api' killed due to out of memory (OOM)"
        )

        task_ui.display_failure_analysis(failed_task)

        mock_task_service.get_task_failure_analysis.assert_called_once_with(failed_task)
        assert any("Failure Analysis" in str(call) for call in mock_print.call_args_list)
        assert any("memory" in str(call) for call in mock_print.call_args_list)

    def test_build_task_history_choices_includes_history_option(self):
        """Test that task feature choices include task history option."""
        # Import the function directly to test it
        from lazy_ecs.features.task.ui import _build_task_feature_choices

        containers = [{"name": "web-api", "image": "nginx:latest"}]
        choices = _build_task_feature_choices(containers)

        # Check that task history option is included
        history_choices = [c for c in choices if "task history" in c["name"].lower()]
        assert len(history_choices) > 0
        assert any("task history" in choice["name"].lower() for choice in history_choices)
