"""Container logs feature."""

from __future__ import annotations

from typing import TYPE_CHECKING

import boto3

from ....core.base import BaseAWSService

if TYPE_CHECKING:
    from mypy_boto3_ecs.client import ECSClient
    from mypy_boto3_logs.client import CloudWatchLogsClient
    from mypy_boto3_logs.type_defs import OutputLogEventTypeDef


class LogsFeature(BaseAWSService):
    """Feature for container logs operations."""

    def __init__(self, ecs_client: ECSClient) -> None:
        super().__init__(ecs_client)

    def get_container_logs(self, log_group: str, log_stream: str, lines: int = 50) -> list[OutputLogEventTypeDef]:
        """Get container logs from CloudWatch."""
        logs_client: CloudWatchLogsClient = boto3.client("logs")

        response = logs_client.get_log_events(
            logGroupName=log_group, logStreamName=log_stream, limit=lines, startFromHead=False
        )
        return response.get("events", [])

    def list_log_groups(self, cluster_name: str, container_name: str) -> list[str]:
        """List available log groups for debugging."""
        logs_client: CloudWatchLogsClient = boto3.client("logs")

        response = logs_client.describe_log_groups(limit=50)
        groups = response.get("logGroups", [])

        relevant_groups = []
        for group in groups[:10]:
            name = group["logGroupName"]
            if cluster_name.lower() in name.lower() or container_name.lower() in name.lower() or "ecs" in name.lower():
                relevant_groups.append(name)

        return relevant_groups
