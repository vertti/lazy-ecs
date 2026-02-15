from __future__ import annotations

from collections.abc import Generator
from contextlib import suppress
from os import environ
from typing import TYPE_CHECKING, Any

from botocore.exceptions import BotoCoreError, ClientError

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


def build_log_group_arn(region: str, account_id: str, log_group: str) -> str:
    return f"arn:aws:logs:{region}:{account_id}:log-group:{log_group}"


def build_log_stream_name(stream_prefix: str, container_name: str, task_id: str) -> str:
    return f"{stream_prefix}/{container_name}/{task_id}"


class LiveTailError(RuntimeError):
    pass


def _format_client_error(error: ClientError) -> str:
    error_details = error.response.get("Error", {})
    code = error_details.get("Code")
    message = error_details.get("Message", str(error))
    return f"{code}: {message}" if code else message


class ContainerService:
    def __init__(
        self,
        ecs_client: ECSClient,
        task_service: TaskService,
        sts_client: STSClient | None = None,
        logs_client: CloudWatchLogsClient | None = None,
    ) -> None:
        self.ecs_client = ecs_client
        self.task_service = task_service
        self.sts_client = sts_client
        self.logs_client = logs_client

    def get_container_context(self, cluster_name: str, task_arn: str, container_name: str) -> ContainerContext | None:
        result = self.task_service.get_task_and_definition(cluster_name, task_arn)
        if not result:
            return None

        _task, task_definition = result

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
        self,
        task_definition: TaskDefinitionTypeDef,
        container_name: str,
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

        log_stream = build_log_stream_name(stream_prefix, container_name, context.task_id)

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
            logGroupName=log_group,
            logStreamName=log_stream,
            limit=lines,
            startFromHead=False,
        )
        return response.get("events", [])

    def get_container_logs_filtered(
        self,
        log_group: str,
        log_stream: str,
        filter_pattern: str,
        lines: int = 50,
    ) -> list[FilteredLogEventTypeDef]:
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
        self,
        log_group: str,
        log_stream: str,
        event_filter_pattern: str = "",
        aws_account_id: str | None = None,
    ) -> Generator[StartLiveTailResponseStreamTypeDef | LiveTailSessionLogEventTypeDef]:
        if not self.logs_client:
            message = "CloudWatch Logs client is not configured"
            raise LiveTailError(message)

        region = self.ecs_client.meta.region_name
        if not region:
            message = "AWS region is not configured for ECS client"
            raise LiveTailError(message)

        resolved_account_id = aws_account_id
        if resolved_account_id is None:
            if self.sts_client:
                try:
                    resolved_account_id = self.sts_client.get_caller_identity().get("Account")
                except ClientError as e:
                    details = _format_client_error(e)
                    error_message = f"Failed to get AWS account ID from STS: {details}"
                    raise LiveTailError(error_message) from e
                except BotoCoreError as e:
                    error_message = f"Failed to get AWS account ID from STS: {e}"
                    raise LiveTailError(error_message) from e
            else:
                resolved_account_id = environ.get("AWS_ACCOUNT_ID")

        if not resolved_account_id:
            error_message = "AWS account ID is required for live tail. Configure STS access or set AWS_ACCOUNT_ID."
            raise LiveTailError(error_message)

        log_group_arn = build_log_group_arn(region, resolved_account_id, log_group)
        try:
            response = self.logs_client.start_live_tail(
                logGroupIdentifiers=[log_group_arn],
                logStreamNames=[log_stream],
                logEventFilterPattern=event_filter_pattern,
            )
        except ClientError as e:
            details = _format_client_error(e)
            error_message = f"Failed to start CloudWatch live tail: {details}"
            raise LiveTailError(error_message) from e
        except BotoCoreError as e:
            error_message = f"Failed to start CloudWatch live tail: {e}"
            raise LiveTailError(error_message) from e

        response_stream = response.get("responseStream")
        if not response_stream:
            message = "CloudWatch live tail did not return a response stream"
            raise LiveTailError(message)

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

        volumes_map = {}
        for volume in context.task_definition.get("volumes", []):
            volume_name = volume["name"]
            host_config = volume.get("host", {})
            host_path = host_config.get("sourcePath") if host_config else None
            volumes_map[volume_name] = host_path

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
