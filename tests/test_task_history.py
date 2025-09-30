"""Tests for task history and failure analysis functionality."""

from datetime import datetime
from typing import Any

import pytest

from lazy_ecs.features.task.task import TaskService


class TestTaskHistoryParsing:
    """Test parsing task history and failure information."""

    def test_parse_stopped_task_with_stop_code(self):
        """Test parsing stopped task with stop code."""
        _mock_task_data: dict[str, Any] = {
            "taskArn": "arn:aws:ecs:us-east-1:123456789012:task/cluster/task-id",
            "lastStatus": "STOPPED",
            "desiredStatus": "STOPPED",
            "stopCode": "TaskFailedToStart",
            "stoppedReason": "Essential container in task exited",
            "stoppedAt": datetime(2024, 1, 15, 10, 30, 0),
            "createdAt": datetime(2024, 1, 15, 10, 25, 0),
            "startedAt": datetime(2024, 1, 15, 10, 26, 0),
            "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/web-api:5",
            "containers": [
                {
                    "name": "web-api",
                    "exitCode": 137,
                    "reason": "OutOfMemoryError: Container killed due to memory usage",
                    "healthStatus": "UNHEALTHY",
                    "lastStatus": "STOPPED",
                }
            ],
        }

        _expected_history = {
            "task_arn": "arn:aws:ecs:us-east-1:123456789012:task/cluster/task-id",
            "task_definition_name": "web-api",
            "task_definition_revision": "5",
            "last_status": "STOPPED",
            "desired_status": "STOPPED",
            "stop_code": "TaskFailedToStart",
            "stopped_reason": "Essential container in task exited",
            "created_at": datetime(2024, 1, 15, 10, 25, 0),
            "started_at": datetime(2024, 1, 15, 10, 26, 0),
            "stopped_at": datetime(2024, 1, 15, 10, 30, 0),
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

        result = TaskService._parse_task_history(_mock_task_data)  # type: ignore
        assert result == _expected_history

    def test_parse_running_task_no_failure_info(self):
        """Test parsing running task with no failure information."""
        _mock_task_data: dict[str, Any] = {
            "taskArn": "arn:aws:ecs:us-east-1:123456789012:task/cluster/task-id-2",
            "lastStatus": "RUNNING",
            "desiredStatus": "RUNNING",
            "createdAt": datetime(2024, 1, 15, 11, 0, 0),
            "startedAt": datetime(2024, 1, 15, 11, 1, 0),
            "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/web-api:6",
            "containers": [{"name": "web-api", "healthStatus": "HEALTHY", "lastStatus": "RUNNING"}],
        }

        _expected_history = {
            "task_arn": "arn:aws:ecs:us-east-1:123456789012:task/cluster/task-id-2",
            "task_definition_name": "web-api",
            "task_definition_revision": "6",
            "last_status": "RUNNING",
            "desired_status": "RUNNING",
            "stop_code": None,
            "stopped_reason": None,
            "created_at": datetime(2024, 1, 15, 11, 0, 0),
            "started_at": datetime(2024, 1, 15, 11, 1, 0),
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
        }

        result = TaskService._parse_task_history(_mock_task_data)  # type: ignore
        assert result == _expected_history

    def test_analyze_oom_kill_failure(self):
        """Test analysis of OOM kill failure."""
        result = TaskService._analyze_container_failure(
            "web-api",
            137,
            "OutOfMemoryError: Container killed due to memory usage",
            "TaskFailedToStart",
            "Essential container in task exited",
        )
        assert "🔴" in result
        assert "memory" in result.lower()
        assert "web-api" in result

    def test_analyze_successful_completion(self):
        """Test analysis of successful task completion."""
        result = TaskService._analyze_task_failure(None, None)
        assert "✅" in result
        assert "completed successfully" in result.lower()

    def test_analyze_timeout_failure(self):
        """Test analysis of timeout failure."""
        result = TaskService._analyze_container_failure(
            "web-api", 137, "Task killed", "TaskFailedToStart", "Task timed out"
        )
        assert "⏰" in result
        assert "timeout" in result.lower()


class TestTaskHistoryService:
    """Test task history service methods."""

    @pytest.fixture
    def mock_ecs_client(self, mock_paginated_client):
        """Mock ECS client for testing."""
        pages = [
            {
                "taskArns": [
                    "arn:aws:ecs:us-east-1:123456789012:task/cluster/running-task",
                    "arn:aws:ecs:us-east-1:123456789012:task/cluster/stopped-task",
                ]
            }
        ]
        client = mock_paginated_client(pages)

        client.describe_tasks.return_value = {
            "tasks": [
                {
                    "taskArn": "arn:aws:ecs:us-east-1:123456789012:task/cluster/stopped-task",
                    "lastStatus": "STOPPED",
                    "stopCode": "TaskFailedToStart",
                    "stoppedReason": "Essential container in task exited",
                    "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/web-api:5",
                    "containers": [{"name": "web-api", "exitCode": 137}],
                }
            ]
        }
        return client

    def test_get_task_history_includes_stopped_tasks(self, mock_ecs_client):
        """Test getting task history includes stopped tasks."""
        _service = TaskService(mock_ecs_client)

        result = _service.get_task_history("test-cluster", "web-service")
        assert len(result) > 0
        assert any(task["last_status"] == "STOPPED" for task in result)

    def test_get_task_history_handles_no_stopped_tasks(self, mock_paginated_client):
        """Test getting task history when no stopped tasks exist."""
        pages = [{"taskArns": []}]
        client = mock_paginated_client(pages)

        _service = TaskService(client)

        result = _service.get_task_history("test-cluster", "web-service")
        assert result == []
