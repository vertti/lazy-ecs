"""Tests for task comparison service operations."""

from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

from lazy_ecs.features.task.comparison import TaskComparisonService


@pytest.fixture
def ecs_client_with_task_definitions():
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")

        client.register_task_definition(
            family="my-app",
            containerDefinitions=[
                {
                    "name": "web",
                    "image": "nginx:1.19",
                    "memory": 512,
                    "environment": [{"name": "ENV", "value": "dev"}],
                },
            ],
        )

        client.register_task_definition(
            family="my-app",
            containerDefinitions=[
                {
                    "name": "web",
                    "image": "nginx:1.20",
                    "memory": 512,
                    "environment": [{"name": "ENV", "value": "staging"}],
                },
            ],
        )

        client.register_task_definition(
            family="my-app",
            containerDefinitions=[
                {
                    "name": "web",
                    "image": "nginx:1.21",
                    "memory": 1024,
                    "environment": [{"name": "ENV", "value": "production"}],
                },
            ],
        )

        yield client


def test_list_task_definition_revisions(ecs_client_with_task_definitions):
    service = TaskComparisonService(ecs_client_with_task_definitions)

    revisions = service.list_task_definition_revisions("my-app", limit=10)

    assert len(revisions) == 3
    assert revisions[0]["revision"] == 3
    assert revisions[1]["revision"] == 2
    assert revisions[2]["revision"] == 1
    assert all(r["family"] == "my-app" for r in revisions)


def test_list_task_definition_revisions_respects_limit(ecs_client_with_task_definitions):
    service = TaskComparisonService(ecs_client_with_task_definitions)

    revisions = service.list_task_definition_revisions("my-app", limit=2)

    assert len(revisions) == 2
    assert revisions[0]["revision"] == 3
    assert revisions[1]["revision"] == 2


def test_get_task_definitions_for_comparison(ecs_client_with_task_definitions):
    service = TaskComparisonService(ecs_client_with_task_definitions)

    source_arn = "arn:aws:ecs:us-east-1:123456789012:task-definition/my-app:2"
    target_arn = "arn:aws:ecs:us-east-1:123456789012:task-definition/my-app:3"

    source, target = service.get_task_definitions_for_comparison(source_arn, target_arn)

    assert source["family"] == "my-app"
    assert source["revision"] == 2
    assert target["family"] == "my-app"
    assert target["revision"] == 3

    assert len(source["containers"]) == 1
    assert len(target["containers"]) == 1
    assert source["containers"][0]["image"] == "nginx:1.20"
    assert target["containers"][0]["image"] == "nginx:1.21"
