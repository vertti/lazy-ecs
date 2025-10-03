"""Tests for service metrics fetching from CloudWatch."""

from datetime import UTC, datetime, timedelta

import boto3
import pytest
from moto import mock_aws

from lazy_ecs.features.service.metrics import get_service_metrics


@pytest.fixture
def cloudwatch_client_with_metrics():
    """Create a mocked CloudWatch client with test metrics."""
    with mock_aws():
        client = boto3.client("cloudwatch", region_name="us-east-1")
        utc_now = datetime.now(tz=UTC)

        namespace = "AWS/ECS"
        cluster_name = "production"
        service_name = "web-api"

        for minutes_ago in range(60, 0, -5):
            timestamp = utc_now - timedelta(minutes=minutes_ago)

            cpu_value = 45.0 + (minutes_ago % 10)
            client.put_metric_data(
                Namespace=namespace,
                MetricData=[
                    {
                        "MetricName": "CPUUtilization",
                        "Value": cpu_value,
                        "Timestamp": timestamp,
                        "Dimensions": [
                            {"Name": "ClusterName", "Value": cluster_name},
                            {"Name": "ServiceName", "Value": service_name},
                        ],
                    }
                ],
            )

            memory_value = 75.0 + (minutes_ago % 15)
            client.put_metric_data(
                Namespace=namespace,
                MetricData=[
                    {
                        "MetricName": "MemoryUtilization",
                        "Value": memory_value,
                        "Timestamp": timestamp,
                        "Dimensions": [
                            {"Name": "ClusterName", "Value": cluster_name},
                            {"Name": "ServiceName", "Value": service_name},
                        ],
                    }
                ],
            )

        yield client


def test_get_service_metrics_returns_cpu_and_memory_data(cloudwatch_client_with_metrics):
    metrics = get_service_metrics(
        cloudwatch_client=cloudwatch_client_with_metrics,
        cluster_name="production",
        service_name="web-api",
        hours=1,
    )

    assert metrics is not None
    assert "cpu" in metrics
    assert "memory" in metrics


def test_get_service_metrics_cpu_contains_statistics(cloudwatch_client_with_metrics):
    metrics = get_service_metrics(
        cloudwatch_client=cloudwatch_client_with_metrics,
        cluster_name="production",
        service_name="web-api",
        hours=1,
    )

    assert metrics is not None
    cpu = metrics["cpu"]
    assert "current" in cpu
    assert "average" in cpu
    assert "maximum" in cpu
    assert "minimum" in cpu

    assert isinstance(cpu["current"], float)
    assert isinstance(cpu["average"], float)
    assert isinstance(cpu["maximum"], float)
    assert isinstance(cpu["minimum"], float)


def test_get_service_metrics_memory_contains_statistics(cloudwatch_client_with_metrics):
    metrics = get_service_metrics(
        cloudwatch_client=cloudwatch_client_with_metrics,
        cluster_name="production",
        service_name="web-api",
        hours=1,
    )

    assert metrics is not None
    memory = metrics["memory"]
    assert "current" in memory
    assert "average" in memory
    assert "maximum" in memory
    assert "minimum" in memory

    assert isinstance(memory["current"], float)
    assert isinstance(memory["average"], float)
    assert isinstance(memory["maximum"], float)
    assert isinstance(memory["minimum"], float)


def test_get_service_metrics_returns_none_when_no_data():
    with mock_aws():
        client = boto3.client("cloudwatch", region_name="us-east-1")

        metrics = get_service_metrics(
            cloudwatch_client=client,
            cluster_name="nonexistent",
            service_name="nonexistent",
            hours=1,
        )

        assert metrics is None
