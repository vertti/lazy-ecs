"""CloudWatch metrics operations for ECS services."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from ...core.types import MetricStatistics, ServiceMetrics

if TYPE_CHECKING:
    from mypy_boto3_cloudwatch.client import CloudWatchClient
    from mypy_boto3_cloudwatch.type_defs import DatapointTypeDef


def get_service_metrics(
    cloudwatch_client: CloudWatchClient,
    cluster_name: str,
    service_name: str,
    hours: int = 1,
) -> ServiceMetrics | None:
    """Fetch CPU and Memory utilization metrics for an ECS service from CloudWatch."""
    utc_now = datetime.now(tz=UTC)
    start_time = utc_now - timedelta(hours=hours)
    end_time = utc_now

    cpu_stats = _get_metric_statistics(
        cloudwatch_client=cloudwatch_client,
        cluster_name=cluster_name,
        service_name=service_name,
        metric_name="CPUUtilization",
        start_time=start_time,
        end_time=end_time,
    )

    memory_stats = _get_metric_statistics(
        cloudwatch_client=cloudwatch_client,
        cluster_name=cluster_name,
        service_name=service_name,
        metric_name="MemoryUtilization",
        start_time=start_time,
        end_time=end_time,
    )

    if cpu_stats is None or memory_stats is None:
        return None

    return {"cpu": cpu_stats, "memory": memory_stats}


def format_metrics_display(metrics: ServiceMetrics) -> list[str]:
    """Format service metrics into human-readable display lines."""
    lines = []

    cpu = metrics["cpu"]
    memory = metrics["memory"]

    cpu_line = (
        f"CPU:    Current: {cpu['current']:5.1f}%  |  Avg: {cpu['average']:5.1f}%  |  "
        f"Peak: {cpu['maximum']:5.1f}%  |  Low: {cpu['minimum']:5.1f}%"
    )
    memory_line = (
        f"Memory: Current: {memory['current']:5.1f}%  |  Avg: {memory['average']:5.1f}%  |  "
        f"Peak: {memory['maximum']:5.1f}%  |  Low: {memory['minimum']:5.1f}%"
    )

    lines.append(cpu_line)
    lines.append(memory_line)

    return lines


def _get_metric_statistics(
    cloudwatch_client: CloudWatchClient,
    cluster_name: str,
    service_name: str,
    metric_name: str,
    start_time: datetime,
    end_time: datetime,
) -> MetricStatistics | None:
    """Fetch statistics for a single metric."""
    response = cloudwatch_client.get_metric_statistics(
        Namespace="AWS/ECS",
        MetricName=metric_name,
        Dimensions=[
            {"Name": "ClusterName", "Value": cluster_name},
            {"Name": "ServiceName", "Value": service_name},
        ],
        StartTime=start_time,
        EndTime=end_time,
        Period=300,
        Statistics=["Average", "Maximum", "Minimum"],
    )

    datapoints: list[DatapointTypeDef] = response.get("Datapoints", [])

    if not datapoints:
        return None

    sorted_datapoints = sorted(datapoints, key=lambda x: x.get("Timestamp", datetime.min), reverse=True)

    current_datapoint = sorted_datapoints[0]
    current_value = current_datapoint.get("Average", 0.0)

    all_averages = [dp.get("Average", 0.0) for dp in datapoints if "Average" in dp]
    average_value = sum(all_averages) / len(all_averages) if all_averages else 0.0

    all_maximums = [dp.get("Maximum", 0.0) for dp in datapoints if "Maximum" in dp]
    maximum_value = max(all_maximums) if all_maximums else 0.0

    all_minimums = [dp.get("Minimum", 0.0) for dp in datapoints if "Minimum" in dp]
    minimum_value = min(all_minimums) if all_minimums else 0.0

    return {
        "current": current_value,
        "average": average_value,
        "maximum": maximum_value,
        "minimum": minimum_value,
    }
