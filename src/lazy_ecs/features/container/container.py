"""Container operations for ECS."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import suppress
from os import environ
from typing import TYPE_CHECKING, Any

from ...core.base import BaseAWSService
from ...core.context import ContainerContext
from ...core.types import LogConfig

if TYPE_CHECKING:
    from mypy_boto3_ecs.client import ECSClient
    from mypy_boto3_ecs.type_defs import ContainerDefinitionOutputTypeDef, TaskDefinitionTypeDef
    from mypy_boto3_logs.client import CloudWatchLogsClient
    from mypy_boto3_logs.type_defs import (
        FilteredLogEventTypeDef,
        LiveTailSessionLogEventTypeDef,
        OutputLogEventTypeDef,
        StartLiveTailResponseStreamTypeDef,
    )
    from mypy_boto3_sts.client import STSClient

    from ..task.task import TaskService


class ContainerService(BaseAWSService):
    """Service for ECS container operations."""

    def __init__(
        self,
        ecs_client: ECSClient,
        task_service: TaskService,
        sts_client: STSClient | None = None,
        logs_client: CloudWatchLogsClient | None = None,
    ) -> None:
        super().__init__(ecs_client)
        self.task_service = task_service
        self.sts_client = sts_client
        self.logs_client = logs_client

    def get_container_context(self, cluster_name: str, task_arn: str, container_name: str) -> ContainerContext | None:
        """Create a rich container context for operations."""
        result = self.task_service.get_task_and_definition(cluster_name, task_arn)
        if not result:
            return None

        _task, task_definition = result

        # Find the container definition
        for container_def in task_definition["containerDefinitions"]:
            if container_def["name"] == container_name:
                return ContainerContext(
                    cluster_name=cluster_name,
                    service_name="",  # We don't always have service name in this context
                    task_arn=task_arn,
                    container_name=container_name,
                    task_definition=task_definition,
                    container_definition=container_def,
                )

        return None

    def get_container_definition(
        self, task_definition: TaskDefinitionTypeDef, container_name: str
    ) -> ContainerDefinitionOutputTypeDef | None:
        for container_def in task_definition["containerDefinitions"]:
            if container_def["name"] == container_name:
                return container_def
        return None

    def get_log_config(self, cluster_name: str, task_arn: str, container_name: str) -> LogConfig | None:
        context = self.get_container_context(cluster_name, task_arn, container_name)
        if not context:
            return None

        log_config = context.container_definition.get("logConfiguration", {})

        if log_config.get("logDriver") != "awslogs":
            return None

        options = log_config.get("options") or {}
        log_group = options.get("awslogs-group") if options else None
        stream_prefix = options.get("awslogs-stream-prefix", "ecs") if options else "ecs"

        if not log_group:
            return None

        log_stream = f"{stream_prefix}/{container_name}/{context.task_id}"

        return {"log_group": log_group, "log_stream": log_stream}

    def get_environment_variables(self, context: ContainerContext) -> dict[str, str]:
        environment = context.container_definition.get("environment", [])
        return {env_var["name"]: env_var["value"] for env_var in environment}

    def get_secrets(self, context: ContainerContext) -> dict[str, str]:
        secrets = context.container_definition.get("secrets", [])
        return {secret["name"]: secret["valueFrom"] for secret in secrets}

    def get_container_logs(self, log_group: str, log_stream: str, lines: int = 50) -> list[OutputLogEventTypeDef]:
        if not self.logs_client:
            return []
        response = self.logs_client.get_log_events(
            logGroupName=log_group, logStreamName=log_stream, limit=lines, startFromHead=False
        )
        return response.get("events", [])

    def get_container_logs_filtered(
        self, log_group: str, log_stream: str, filter_pattern: str, lines: int = 50
    ) -> list[FilteredLogEventTypeDef]:
        """Get container logs with CloudWatch filter pattern applied."""
        if not self.logs_client:
            return []
        response = self.logs_client.filter_log_events(
            logGroupName=log_group,
            logStreamNames=[log_stream],
            filterPattern=filter_pattern,
            limit=lines,
        )
        return response.get("events", [])

    def get_live_container_logs_tail(
        self, log_group: str, log_stream: str, event_filter_pattern: str = ""
    ) -> Generator[StartLiveTailResponseStreamTypeDef | LiveTailSessionLogEventTypeDef]:
        """Get container logs in real time from CloudWatch."""
        if not self.logs_client:
            return
        region = self.ecs_client.meta.region_name
        aws_account_id = (
            (lambda: self.sts_client.get_caller_identity().get("Account"))()
            if self.sts_client
            else environ.get("AWS_ACCOUNT_ID")
        )
        if not region or not aws_account_id:
            return
        log_group_arn = f"arn:aws:logs:{region}:{aws_account_id}:log-group:{log_group}"
        response = self.logs_client.start_live_tail(
            logGroupIdentifiers=[log_group_arn],
            logStreamNames=[log_stream],
            logEventFilterPattern=event_filter_pattern,
        )
        response_stream = response.get("responseStream")
        try:
            for event in response_stream:
                if "sessionStart" in event:
                    continue
                elif "sessionUpdate" in event:
                    log_events = event.get("sessionUpdate", {}).get("sessionResults", [])
                    yield from log_events
                else:
                    yield event
        finally:
            # Properly close the response stream
            if hasattr(response_stream, "close"):
                with suppress(Exception):
                    response_stream.close()

    def list_log_groups(self, cluster_name: str, container_name: str) -> list[str]:
        if not self.logs_client:
            return []

        response = self.logs_client.describe_log_groups(limit=50)
        groups = response.get("logGroups", [])

        relevant_groups = []
        for group in groups[:10]:
            name = group["logGroupName"]
            if cluster_name.lower() in name.lower() or container_name.lower() in name.lower() or "ecs" in name.lower():
                relevant_groups.append(name)

        return relevant_groups

    def get_port_mappings(self, context: ContainerContext) -> list[dict[str, Any]]:
        port_mappings = context.container_definition.get("portMappings", [])
        return [dict(mapping) for mapping in port_mappings]

    def get_volume_mounts(self, context: ContainerContext) -> list[dict[str, Any]]:
        mount_points = context.container_definition.get("mountPoints", [])
        if not mount_points:
            return []

        # Build volume lookup map from task definition volumes
        volumes_map = {}
        for volume in context.task_definition.get("volumes", []):
            volume_name = volume["name"]
            host_config = volume.get("host", {})
            host_path = host_config.get("sourcePath") if host_config else None
            volumes_map[volume_name] = host_path

        # Build volume mounts with resolved host paths
        volume_mounts = []
        for mount_point in mount_points:
            source_volume = mount_point["sourceVolume"]
            host_path = volumes_map.get(source_volume)

            volume_mount = {
                "source_volume": source_volume,
                "container_path": mount_point["containerPath"],
                "read_only": mount_point.get("readOnly", False),
                "host_path": host_path,
            }
            volume_mounts.append(volume_mount)

        return volume_mounts
