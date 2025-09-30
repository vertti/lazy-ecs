"""Tests for core utility functions."""

import time

from lazy_ecs.core.utils import determine_service_status, extract_name_from_arn, paginate_aws_list, show_spinner


def test_extract_name_from_arn():
    """Test extracting resource names from AWS ARNs."""
    # Test cluster ARN
    cluster_arn = "arn:aws:ecs:us-east-1:123456789012:cluster/production"
    assert extract_name_from_arn(cluster_arn) == "production"

    # Test service ARN
    service_arn = "arn:aws:ecs:us-east-1:123456789012:service/production/web-api"
    assert extract_name_from_arn(service_arn) == "web-api"

    # Test task ARN
    task_arn = "arn:aws:ecs:us-east-1:123456789012:task/production/abc123def456"
    assert extract_name_from_arn(task_arn) == "abc123def456"

    # Test simple case
    simple_name = "just-a-name"
    assert extract_name_from_arn(simple_name) == "just-a-name"


def test_determine_service_status_healthy():
    """Test service status determination for healthy service."""
    icon, status = determine_service_status(running_count=3, desired_count=3, pending_count=0)
    assert icon == "✅"
    assert status == "HEALTHY"


def test_determine_service_status_scaling():
    """Test service status determination for scaling service."""
    icon, status = determine_service_status(running_count=1, desired_count=3, pending_count=2)
    assert icon == "⚠️"
    assert status == "SCALING"


def test_determine_service_status_over_scaled():
    """Test service status determination for over-scaled service."""
    icon, status = determine_service_status(running_count=5, desired_count=3, pending_count=0)
    assert icon == "🔴"
    assert status == "OVER_SCALED"


def test_determine_service_status_pending():
    """Test service status determination for pending service."""
    icon, status = determine_service_status(running_count=3, desired_count=3, pending_count=1)
    assert icon == "🟡"
    assert status == "PENDING"


def test_determine_service_status_zero_counts():
    """Test service status determination with zero counts."""
    icon, status = determine_service_status(running_count=0, desired_count=0, pending_count=0)
    assert icon == "✅"
    assert status == "HEALTHY"


def test_show_spinner():
    """Test spinner context manager works without errors."""
    with show_spinner():
        time.sleep(0.01)  # Brief pause to simulate work


def test_paginate_aws_list_single_page(mock_paginated_client):
    pages = [{"clusterArns": ["arn:aws:ecs:us-east-1:123:cluster/prod"]}]
    mock_client = mock_paginated_client(pages)

    result = paginate_aws_list(mock_client, "list_clusters", "clusterArns")

    assert result == ["arn:aws:ecs:us-east-1:123:cluster/prod"]
    mock_client.get_paginator.assert_called_once_with("list_clusters")


def test_paginate_aws_list_multiple_pages(mock_paginated_client):
    pages = [
        {"serviceArns": ["arn:1", "arn:2"]},
        {"serviceArns": ["arn:3", "arn:4"]},
        {"serviceArns": ["arn:5"]},
    ]
    mock_client = mock_paginated_client(pages)

    result = paginate_aws_list(mock_client, "list_services", "serviceArns", cluster="production")

    assert result == ["arn:1", "arn:2", "arn:3", "arn:4", "arn:5"]
    mock_client.get_paginator.assert_called_once_with("list_services")


def test_paginate_aws_list_empty_results(mock_paginated_client):
    pages = [{"clusterArns": []}]
    mock_client = mock_paginated_client(pages)

    result = paginate_aws_list(mock_client, "list_clusters", "clusterArns")

    assert result == []


def test_paginate_aws_list_missing_key(mock_paginated_client):
    pages = [{}]
    mock_client = mock_paginated_client(pages)

    result = paginate_aws_list(mock_client, "list_clusters", "clusterArns")

    assert result == []
