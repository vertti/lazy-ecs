"""AWS Console URL construction for ECS resources."""

from __future__ import annotations


def build_cluster_url(region: str, cluster_name: str) -> str:
    """Build AWS console URL for an ECS cluster."""
    return f"https://{region}.console.aws.amazon.com/ecs/v2/clusters/{cluster_name}"


def build_service_url(region: str, cluster_name: str, service_name: str) -> str:
    """Build AWS console URL for an ECS service."""
    return f"https://{region}.console.aws.amazon.com/ecs/v2/clusters/{cluster_name}/services/{service_name}"


def build_task_url(region: str, cluster_name: str, task_arn: str) -> str:
    """Build AWS console URL for an ECS task."""
    task_id = _extract_task_id(task_arn)
    return f"https://{region}.console.aws.amazon.com/ecs/v2/clusters/{cluster_name}/tasks/{task_id}"


def _extract_task_id(task_arn: str) -> str:
    """Extract task ID from task ARN or return as-is if already an ID."""
    if task_arn.startswith("arn:aws:ecs:"):
        return task_arn.split("/")[-1]
    return task_arn
