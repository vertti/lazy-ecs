"""Tests for AWS console URL construction."""

from lazy_ecs.core.aws_console import build_cluster_url, build_service_url, build_task_url


def test_build_cluster_url():
    url = build_cluster_url(region="us-east-1", cluster_name="production")
    assert url == "https://us-east-1.console.aws.amazon.com/ecs/v2/clusters/production"


def test_build_cluster_url_with_special_characters():
    url = build_cluster_url(region="eu-west-1", cluster_name="test-cluster-123")
    assert url == "https://eu-west-1.console.aws.amazon.com/ecs/v2/clusters/test-cluster-123"


def test_build_service_url():
    url = build_service_url(region="us-east-1", cluster_name="production", service_name="web-api")
    expected = "https://us-east-1.console.aws.amazon.com/ecs/v2/clusters/production/services/web-api"
    assert url == expected


def test_build_service_url_with_special_characters():
    url = build_service_url(region="ap-southeast-2", cluster_name="test-cluster", service_name="worker-service-v2")
    expected = "https://ap-southeast-2.console.aws.amazon.com/ecs/v2/clusters/test-cluster/services/worker-service-v2"
    assert url == expected


def test_build_task_url():
    task_arn = "arn:aws:ecs:us-east-1:123456789012:task/production/abc123def456"
    url = build_task_url(region="us-east-1", cluster_name="production", task_arn=task_arn)
    expected = "https://us-east-1.console.aws.amazon.com/ecs/v2/clusters/production/tasks/abc123def456"
    assert url == expected


def test_build_task_url_extracts_task_id_from_arn():
    task_arn = "arn:aws:ecs:eu-west-1:987654321098:task/my-cluster/xyz789abc123"
    url = build_task_url(region="eu-west-1", cluster_name="my-cluster", task_arn=task_arn)
    expected = "https://eu-west-1.console.aws.amazon.com/ecs/v2/clusters/my-cluster/tasks/xyz789abc123"
    assert url == expected


def test_build_task_url_with_just_task_id():
    url = build_task_url(region="us-west-2", cluster_name="staging", task_arn="simple-task-id-123")
    expected = "https://us-west-2.console.aws.amazon.com/ecs/v2/clusters/staging/tasks/simple-task-id-123"
    assert url == expected
