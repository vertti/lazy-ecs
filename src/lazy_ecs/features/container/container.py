from __future__ import annotations

import re
from collections.abc import Generator
from contextlib import suppress
from os import environ
from typing import TYPE_CHECKING, Any

from botocore.exceptions import BotoCoreError, ClientError

from ...core.context import ContainerContext
from ...core.types import LogConfig

if TYPE_CHECKING:
    from mypy_boto3_ecs.client import ECSClient
    from mypy_boto3_ecs.type_defs import ContainerDefinitionOutputTypeDef, TaskDefinitionTypeDef, TaskTypeDef
    from mypy_boto3_logs.client import CloudWatchLogsClient
    from mypy_boto3_logs.type_defs import (
        FilteredLogEventTypeDef,
        LiveTailSessionLogEventTypeDef,
        OutputLogEventTypeDef,
        StartLiveTailResponseStreamTypeDef,
    )
    from mypy_boto3_sts.client import STSClient

    from ..task.task import TaskService

    TaskLookupResult = tuple[TaskTypeDef, TaskDefinitionTypeDef] | None
else:
    TaskLookupResult = tuple[dict[str, Any], dict[str, Any]] | None


def build_log_group_arn(region: str, account_id: str, log_group: str) -> str:
    return f"arn:aws:logs:{region}:{account_id}:log-group:{log_group}"


def build_log_stream_name(stream_prefix: str, container_name: str, task_id: str) -> str:
    return f"{stream_prefix}/{container_name}/{task_id}"


class LiveTailError(RuntimeError):
    pass


_CACHE_MISS = object()


def _format_client_error(error: ClientError) -> str:
    error_details = error.response.get("Error", {})
    code = error_details.get("Code")
    message = error_details.get("Message", str(error))
    return f"{code}: {message}" if code else message


def _tokenize_match_terms(value: str) -> set[str]:
    return {term for term in re.split(r"[^a-z0-9]+", value.lower()) if term}


def _score_log_group_name(
    name: str,
    cluster_name: str,
    container_name: str,
    service_name: str | None = None,
    task_family: str | None = None,
) -> int:
    name_lower = name.lower()
    name_terms = _tokenize_match_terms(name_lower)

    def score_target(
        target: str,
        *,
        exact_weight: int,
        contains_weight: int,
        term_weight: int,
    ) -> int:
        normalized = target.strip().lower()
        if not normalized:
            return 0

        score = 0
        if name_lower == normalized or name_lower.endswith(f"/{normalized}"):
            score += exact_weight
        if normalized in name_lower:
            score += contains_weight

        target_terms = _tokenize_match_terms(normalized)
        score += term_weight * len(target_terms & name_terms)
        return score

    score = 0
    score += score_target(cluster_name, exact_weight=120, contains_weight=80, term_weight=20)
    score += score_target(container_name, exact_weight=120, contains_weight=80, term_weight=20)
    if service_name:
        score += score_target(service_name, exact_weight=90, contains_weight=60, term_weight=15)
    if task_family:
        score += score_target(task_family, exact_weight=70, contains_weight=50, term_weight=10)

    if name_lower.startswith("/ecs") or "/ecs/" in name_lower:
        score += 10

    return score


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
        self._task_context_cache: dict[tuple[str, str], TaskLookupResult] = {}

    def clear_context_cache(self) -> None:
        self._task_context_cache.clear()

    def _get_task_and_definition_cached(self, cluster_name: str, task_arn: str) -> TaskLookupResult:
        cache_key = (cluster_name, task_arn)
        cached_result = self._task_context_cache.get(cache_key, _CACHE_MISS)
        if cached_result is not _CACHE_MISS:
            return cached_result

        result = self.task_service.get_task_and_definition(cluster_name, task_arn)
        self._task_context_cache[cache_key] = result
        return result

    def get_container_context(self, cluster_name: str, task_arn: str, container_name: str) -> ContainerContext | None:
        result = self._get_task_and_definition_cached(cluster_name, task_arn)
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

    def list_log_groups(
        self,
        cluster_name: str,
        container_name: str,
        service_name: str | None = None,
        task_family: str | None = None,
    ) -> list[str]:
        if not self.logs_client:
            return []

        # Guardrail to prevent unbounded pagination if tokens keep advancing.
        max_pages = 20
        page = 0

        discovered_groups: list[str] = []
        seen_group_names: set[str] = set()
        seen_tokens: set[str] = set()
        next_token: str | None = None

        while True:
            if page >= max_pages:
                break
            page += 1

            request: dict[str, Any] = {"limit": 50, "logGroupNamePrefix": "/ecs"}
            if next_token:
                request["nextToken"] = next_token

            response = self.logs_client.describe_log_groups(**request)
            groups = response.get("logGroups", [])

            for group in groups:
                name = group.get("logGroupName")
                if isinstance(name, str) and name and name not in seen_group_names:
                    seen_group_names.add(name)
                    discovered_groups.append(name)

            next_token = response.get("nextToken")
            if not next_token or next_token in seen_tokens:
                break
            seen_tokens.add(next_token)

        scored_groups = []
        for name in discovered_groups:
            score = _score_log_group_name(name, cluster_name, container_name, service_name, task_family)
            if score > 0:
                scored_groups.append((score, name))

        scored_groups.sort(key=lambda item: (-item[0], item[1]))
        return [name for _, name in scored_groups[:10]]

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
