"""Task definition comparison functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...core.base import BaseAWSService

if TYPE_CHECKING:
    from mypy_boto3_ecs.client import ECSClient
    from mypy_boto3_ecs.type_defs import TaskDefinitionTypeDef


def normalize_task_definition(raw_task_def: dict[str, Any] | TaskDefinitionTypeDef) -> dict[str, Any]:
    """Normalize task definition by extracting relevant fields and removing AWS metadata."""
    normalized: dict[str, Any] = {
        "family": raw_task_def["family"],
        "revision": raw_task_def["revision"],
        "containers": [],
    }

    if "cpu" in raw_task_def:
        normalized["taskCpu"] = raw_task_def["cpu"]
    if "memory" in raw_task_def:
        normalized["taskMemory"] = raw_task_def["memory"]

    for container_def in raw_task_def.get("containerDefinitions", []):
        container_dict = dict(container_def) if not isinstance(container_def, dict) else container_def
        container = {
            "name": container_dict["name"],
            "image": container_dict["image"],
            "cpu": container_dict.get("cpu"),
            "memory": container_dict.get("memory"),
            "environment": _extract_environment(container_dict),
            "secrets": _extract_secrets(container_dict),
            "ports": container_dict.get("portMappings", []),
            "mountPoints": container_dict.get("mountPoints", []),
            "command": container_dict.get("command"),
            "entryPoint": container_dict.get("entryPoint"),
        }

        if "logConfiguration" in container_dict:
            log_config = container_dict["logConfiguration"]
            if isinstance(log_config, dict):
                container["logDriver"] = log_config.get("logDriver")

        normalized["containers"].append(container)

    return normalized


def _extract_environment(container_def: dict[str, Any]) -> dict[str, str]:
    """Extract environment variables as a dict."""
    env_list = container_def.get("environment", [])
    return {item["name"]: item["value"] for item in env_list}


def _extract_secrets(container_def: dict[str, Any]) -> dict[str, str]:
    """Extract secrets references as a dict."""
    secrets_list = container_def.get("secrets", [])
    return {item["name"]: item["valueFrom"] for item in secrets_list}


def compare_task_definitions(source: dict[str, Any], target: dict[str, Any]) -> list[dict[str, Any]]:
    """Compare two normalized task definitions and return list of changes."""
    changes: list[dict[str, Any]] = []

    _compare_task_level_resources(source, target, changes)
    _compare_containers(source.get("containers", []), target.get("containers", []), changes)

    return changes


def _compare_task_level_resources(
    source: dict[str, Any],
    target: dict[str, Any],
    changes: list[dict[str, Any]],
) -> None:
    """Compare task-level CPU and memory."""
    if source.get("taskCpu") != target.get("taskCpu"):
        changes.append(
            {
                "type": "task_cpu_changed",
                "old": source.get("taskCpu"),
                "new": target.get("taskCpu"),
            },
        )

    if source.get("taskMemory") != target.get("taskMemory"):
        changes.append(
            {
                "type": "task_memory_changed",
                "old": source.get("taskMemory"),
                "new": target.get("taskMemory"),
            },
        )


def _compare_containers(
    source_containers: list[dict[str, Any]],
    target_containers: list[dict[str, Any]],
    changes: list[dict[str, Any]],
) -> None:
    """Compare containers between two task definitions."""
    source_by_name = {c["name"]: c for c in source_containers}
    target_by_name = {c["name"]: c for c in target_containers}

    for name, source_container in source_by_name.items():
        if name in target_by_name:
            _compare_container(source_container, target_by_name[name], changes)


def _compare_container(source: dict[str, Any], target: dict[str, Any], changes: list[dict[str, Any]]) -> None:
    container_name = source["name"]

    _add_change_if_different(source, target, "image", "image_changed", container_name, changes)
    _add_change_if_different(source, target, "cpu", "container_cpu_changed", container_name, changes)
    _add_change_if_different(source, target, "memory", "container_memory_changed", container_name, changes)

    _compare_dicts(source.get("environment", {}), target.get("environment", {}), "env", container_name, changes)
    _compare_dicts(source.get("secrets", {}), target.get("secrets", {}), "secret", container_name, changes)

    _add_change_if_different(source, target, "ports", "ports_changed", container_name, changes, default=[])
    _add_change_if_different(source, target, "command", "command_changed", container_name, changes)
    _add_change_if_different(source, target, "entryPoint", "entrypoint_changed", container_name, changes)
    _add_change_if_different(source, target, "mountPoints", "volumes_changed", container_name, changes, default=[])


def _add_change_if_different(
    source: dict[str, Any],
    target: dict[str, Any],
    key: str,
    change_type: str,
    container_name: str,
    changes: list[dict[str, Any]],
    default: dict[str, Any] | list[Any] | None = None,
) -> None:
    source_val = source.get(key, default)
    target_val = target.get(key, default)
    if source_val != target_val:
        changes.append({"type": change_type, "container": container_name, "old": source_val, "new": target_val})


def _compare_dicts(
    source: dict[str, str],
    target: dict[str, str],
    change_prefix: str,
    container_name: str,
    changes: list[dict[str, Any]],
) -> None:
    for key, value in source.items():
        if key not in target:
            changes.append(
                {"type": f"{change_prefix}_removed", "container": container_name, "key": key, "value": value},
            )
        elif target[key] != value:
            changes.append(
                {
                    "type": f"{change_prefix}_changed",
                    "container": container_name,
                    "key": key,
                    "old": value,
                    "new": target[key],
                },
            )

    for key, value in target.items():
        if key not in source:
            changes.append({"type": f"{change_prefix}_added", "container": container_name, "key": key, "value": value})


class TaskComparisonService(BaseAWSService):
    """Service for task definition comparison operations."""

    def __init__(self, ecs_client: ECSClient) -> None:
        super().__init__(ecs_client)

    def list_task_definition_revisions(self, family: str, limit: int = 10) -> list[dict[str, Any]]:
        response = self.ecs_client.list_task_definitions(familyPrefix=family, sort="DESC")
        task_def_arns = response.get("taskDefinitionArns", [])

        revisions = [
            {
                "arn": arn,
                "family": arn.split("/")[-1].split(":")[0],
                "revision": int(arn.split(":")[-1]),
            }
            for arn in task_def_arns
        ]

        revisions.sort(key=lambda r: r["revision"], reverse=True)
        return revisions[:limit]

    def get_task_definitions_for_comparison(
        self,
        source_arn: str,
        target_arn: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        source_response = self.ecs_client.describe_task_definition(taskDefinition=source_arn)
        target_response = self.ecs_client.describe_task_definition(taskDefinition=target_arn)

        return (
            normalize_task_definition(source_response["taskDefinition"]),
            normalize_task_definition(target_response["taskDefinition"]),
        )
