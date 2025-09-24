"""Tests for service events functionality."""

from datetime import datetime

from lazy_ecs.features.service.service import _categorize_event, _create_service_event


def test_categorize_event_deployment():
    """Test deployment event categorization."""
    deployment_messages = [
        "has started a deployment",
        "task definition updated",
        "service web-api has started deployment",
        "deployment completed successfully",
        "stopped 2 running tasks",
        "has started 3 tasks",
        "registered 1 targets in target-group",
        "deregistered 1 targets in target-group",
    ]

    for message in deployment_messages:
        assert _categorize_event(message) == "deployment"


def test_categorize_event_scaling():
    """Test scaling event categorization."""
    scaling_messages = [
        "has reached a steady state with 3 running tasks",
        "desired count changed from 2 to 4",
        "capacity provider scaling",
        "service is scaling up",
    ]

    for message in scaling_messages:
        assert _categorize_event(message) == "scaling"


def test_categorize_event_failure():
    """Test failure event categorization."""
    failure_messages = [
        "task failed to start",
        "service is unhealthy",
        "unable to place task",
        "deployment failed due to error",
        "task stopped unexpectedly with error",
    ]

    for message in failure_messages:
        assert _categorize_event(message) == "failure"


def test_categorize_event_other():
    """Test other event categorization."""
    other_messages = [
        "ELB health check configuration has been changed",
        "service discovery configuration changed",
        "random message that doesn't fit categories",
        "task definition family revision changed",
    ]

    for message in other_messages:
        assert _categorize_event(message) == "other"


def test_create_service_event():
    """Test service event creation from AWS event data."""
    test_time = datetime(2024, 1, 15, 10, 30, 45)
    aws_event = {
        "id": "event-123",
        "createdAt": test_time,
        "message": "has started a deployment",
    }

    event = _create_service_event(aws_event)

    assert event["id"] == "event-123"
    assert event["created_at"] == test_time
    assert event["message"] == "has started a deployment"
    assert event["event_type"] == "deployment"


def test_create_service_event_minimal():
    """Test service event creation with minimal AWS data."""
    aws_event = {}

    event = _create_service_event(aws_event)

    assert event["id"] == ""
    assert event["created_at"] is None
    assert event["message"] == ""
    assert event["event_type"] == "other"


def test_create_service_event_missing_fields():
    """Test service event creation with some missing fields."""
    aws_event = {
        "message": "task failed to start due to resource constraints",
    }

    event = _create_service_event(aws_event)

    assert event["id"] == ""
    assert event["created_at"] is None
    assert event["message"] == "task failed to start due to resource constraints"
    assert event["event_type"] == "failure"


def test_service_events_sorted_by_time():
    """Test that service events are sorted by creation time, most recent first."""
    from datetime import datetime
    from unittest.mock import Mock

    from lazy_ecs.features.service.service import ServiceService

    mock_client = Mock()
    mock_client.describe_services.return_value = {
        "services": [
            {
                "events": [
                    {
                        "id": "event-1",
                        "createdAt": datetime(2024, 1, 15, 10, 0, 0),
                        "message": "Older event",
                    },
                    {
                        "id": "event-2",
                        "createdAt": datetime(2024, 1, 15, 12, 0, 0),
                        "message": "Newer event",
                    },
                    {
                        "id": "event-3",
                        "createdAt": datetime(2024, 1, 15, 11, 0, 0),
                        "message": "Middle event",
                    },
                ]
            }
        ]
    }

    service = ServiceService(mock_client)
    events = service.get_service_events("test-cluster", "test-service")

    # Should be sorted newest first
    assert len(events) == 3
    assert events[0]["message"] == "Newer event"  # 12:00
    assert events[1]["message"] == "Middle event"  # 11:00
    assert events[2]["message"] == "Older event"  # 10:00
