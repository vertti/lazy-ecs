"""Tests for core utility functions."""

import time

from lazy_ecs.core.utils import (
    batch_items,
    determine_service_status,
    extract_name_from_arn,
    paginate_aws_list,
    print_error,
    print_info,
    print_success,
    print_warning,
    show_spinner,
)


def test_extract_name_from_arn():
    assert extract_name_from_arn("arn:aws:ecs:us-east-1:123456789012:cluster/production") == "production"
    assert extract_name_from_arn("arn:aws:ecs:us-east-1:123456789012:service/production/web-api") == "web-api"
    assert extract_name_from_arn("arn:aws:ecs:us-east-1:123456789012:task/production/abc123def456") == "abc123def456"
    assert extract_name_from_arn("just-a-name") == "just-a-name"


def test_determine_service_status_healthy():
    icon, status = determine_service_status(running_count=3, desired_count=3, pending_count=0)
    assert icon == "✅"
    assert status == "HEALTHY"


def test_determine_service_status_scaling():
    icon, status = determine_service_status(running_count=1, desired_count=3, pending_count=2)
    assert icon == "⚠️"
    assert status == "SCALING"


def test_determine_service_status_over_scaled():
    icon, status = determine_service_status(running_count=5, desired_count=3, pending_count=0)
    assert icon == "🔴"
    assert status == "OVER_SCALED"


def test_determine_service_status_pending():
    icon, status = determine_service_status(running_count=3, desired_count=3, pending_count=1)
    assert icon == "🟡"
    assert status == "PENDING"


def test_determine_service_status_zero_counts():
    icon, status = determine_service_status(running_count=0, desired_count=0, pending_count=0)
    assert icon == "✅"
    assert status == "HEALTHY"


def test_show_spinner():
    with show_spinner():
        time.sleep(0.01)


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


def test_print_success(capsys):
    print_success("Operation completed")
    captured = capsys.readouterr()
    assert "Operation completed" in captured.out


def test_print_error(capsys):
    print_error("Something went wrong")
    captured = capsys.readouterr()
    assert "Something went wrong" in captured.out


def test_print_warning(capsys):
    print_warning("Be careful")
    captured = capsys.readouterr()
    assert "Be careful" in captured.out


def test_print_info(capsys):
    print_info("Informational message")
    captured = capsys.readouterr()
    assert "Informational message" in captured.out


def test_batch_items_empty_list():
    result = list(batch_items([], 5))
    assert result == []


def test_batch_items_single_batch():
    items = [1, 2, 3]
    result = list(batch_items(items, 5))
    assert result == [[1, 2, 3]]


def test_batch_items_multiple_batches():
    items = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    result = list(batch_items(items, 3))
    assert result == [[1, 2, 3], [4, 5, 6], [7, 8, 9]]


def test_batch_items_partial_last_batch():
    items = [1, 2, 3, 4, 5, 6, 7]
    result = list(batch_items(items, 3))
    assert result == [[1, 2, 3], [4, 5, 6], [7]]
