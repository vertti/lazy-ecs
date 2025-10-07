"""Tests for task history and failure analysis functionality."""

from datetime import datetime
from typing import Any
from unittest.mock import Mock

import boto3
import pytest
from moto import mock_aws

from lazy_ecs.features.task.task import TaskService


class TestTaskHistoryParsing:
    """Test parsing task history and failure information."""

    def test_parse_stopped_task_with_stop_code(self):
        task_data: dict[str, Any] = {
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
                },
            ],
        }

        expected = {
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
                },
            ],
        }

        result = TaskService._parse_task_history(task_data)  # type: ignore
        assert result == expected

    def test_parse_running_task_no_failure_info(self):
        """Test parsing running task with no failure information."""
        task_data: dict[str, Any] = {
            "taskArn": "arn:aws:ecs:us-east-1:123456789012:task/cluster/task-id-2",
            "lastStatus": "RUNNING",
            "desiredStatus": "RUNNING",
            "createdAt": datetime(2024, 1, 15, 11, 0, 0),
            "startedAt": datetime(2024, 1, 15, 11, 1, 0),
            "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/web-api:6",
            "containers": [{"name": "web-api", "healthStatus": "HEALTHY", "lastStatus": "RUNNING"}],
        }

        expected = {
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
                },
            ],
        }

        result = TaskService._parse_task_history(task_data)  # type: ignore
        assert result == expected

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

    @pytest.mark.parametrize(
        ("exit_code", "reason", "expected_emoji", "expected_text"),
        [
            (137, "Task killed", "⏰", "timeout"),
            (139, None, "💥", "segmentation fault"),
            (143, None, "🛑", "gracefully stopped"),
            (1, "Application crashed", "❌", "application error"),
            (42, "Unknown error", "🔴", "exit code 42"),
        ],
    )
    def test_analyze_container_failure_exit_codes(self, exit_code, reason, expected_emoji, expected_text):
        result = TaskService._analyze_container_failure("container", exit_code, reason, None, None)
        assert expected_emoji in result
        assert expected_text in result.lower()

    @pytest.mark.parametrize(
        ("stop_code", "reason", "expected_emoji", "expected_text"),
        [
            ("TaskFailedToStart", "CannotPullContainerError: image not found", "📦", "pull container image"),
            ("TaskFailedToStart", "ResourcesNotAvailable: insufficient memory", "⚠️", "insufficient resources"),
            ("TaskFailedToStart", "Some other reason", "🚫", "failed to start"),
            ("ServiceSchedulerInitiated", "Service scaling", "🔄", "service scheduler"),
            ("SpotInterruption", "EC2 spot instance reclaimed", "💸", "spot instance interruption"),
            ("UserInitiated", "Stopped by admin", "👤", "manually stopped"),
        ],
    )
    def test_analyze_task_failure_stop_codes(self, stop_code, reason, expected_emoji, expected_text):
        result = TaskService._analyze_task_failure(stop_code, reason)
        assert expected_emoji in result
        assert expected_text in result.lower()

    def test_get_task_failure_analysis_for_running_task(self):
        task_history = {
            "task_arn": "arn:task",
            "task_definition_name": "app",
            "task_definition_revision": "1",
            "last_status": "RUNNING",
            "desired_status": "RUNNING",
            "stop_code": None,
            "stopped_reason": None,
            "created_at": None,
            "started_at": None,
            "stopped_at": None,
            "containers": [],
        }
        service = TaskService(Mock())

        result = service.get_task_failure_analysis(task_history)  # type: ignore[arg-type]

        assert "✅" in result
        assert "running" in result.lower()

    def test_get_task_failure_analysis_container_failure(self):
        task_history = {
            "task_arn": "arn:task",
            "task_definition_name": "app",
            "task_definition_revision": "1",
            "last_status": "STOPPED",
            "desired_status": "STOPPED",
            "stop_code": "TaskFailedToStart",
            "stopped_reason": "Essential container exited",
            "created_at": None,
            "started_at": None,
            "stopped_at": None,
            "containers": [
                {
                    "name": "web",
                    "exit_code": 1,
                    "reason": "App crashed",
                    "health_status": None,
                    "last_status": "STOPPED",
                }
            ],
        }
        service = TaskService(Mock())

        result = service.get_task_failure_analysis(task_history)  # type: ignore[arg-type]

        assert "❌" in result
        assert "application error" in result.lower()

    def test_get_task_failure_analysis_task_level_failure(self):
        task_history = {
            "task_arn": "arn:task",
            "task_definition_name": "app",
            "task_definition_revision": "1",
            "last_status": "STOPPED",
            "desired_status": "STOPPED",
            "stop_code": "TaskFailedToStart",
            "stopped_reason": "CannotPullContainerError",
            "created_at": None,
            "started_at": None,
            "stopped_at": None,
            "containers": [
                {"name": "web", "exit_code": None, "reason": None, "health_status": None, "last_status": "STOPPED"}
            ],
        }
        service = TaskService(Mock())

        result = service.get_task_failure_analysis(task_history)  # type: ignore[arg-type]

        assert "📦" in result
        assert "pull container image" in result.lower()


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
                ],
            },
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
                },
            ],
        }
        return client

    def test_get_task_history_includes_stopped_tasks(self, mock_ecs_client):
        """Test getting task history includes stopped tasks."""
        service = TaskService(mock_ecs_client)

        result = service.get_task_history("test-cluster", "web-service")
        assert len(result) > 0
        assert any(task["last_status"] == "STOPPED" for task in result)

    def test_get_task_history_handles_no_stopped_tasks(self, mock_paginated_client):
        """Test getting task history when no stopped tasks exist."""
        pages = [{"taskArns": []}]
        client = mock_paginated_client(pages)

        service = TaskService(client)

        result = service.get_task_history("test-cluster", "web-service")
        assert result == []


def test_get_task_history_with_more_than_100_tasks():
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")
        client.create_cluster(clusterName="production")

        client.register_task_definition(
            family="app-task",
            containerDefinitions=[{"name": "app", "image": "nginx", "memory": 256}],
        )

        client.create_service(
            cluster="production",
            serviceName="app-service",
            taskDefinition="app-task",
            desiredCount=150,
        )

        for _ in range(150):
            client.run_task(
                cluster="production",
                taskDefinition="app-task",
                launchType="FARGATE",
                networkConfiguration={
                    "awsvpcConfiguration": {
                        "subnets": ["subnet-12345"],
                        "assignPublicIp": "ENABLED",
                    }
                },
            )

        service = TaskService(client)
        task_history = service.get_task_history("production", "app-service")

        assert len(task_history) == 150
        for task in task_history:
            assert "task_arn" in task
            assert "last_status" in task
            assert "task_definition_name" in task
