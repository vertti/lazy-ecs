"""Service operations for ECS."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from ...core.base import BaseAWSService
from ...core.types import ServiceEvent, ServiceInfo
from ...core.utils import determine_service_status, extract_name_from_arn, paginate_aws_list

if TYPE_CHECKING:
    from typing import Any

    from mypy_boto3_ecs.client import ECSClient
    from mypy_boto3_ecs.type_defs import ServiceTypeDef


class ServiceService(BaseAWSService):
    """Service for ECS service operations."""

    def __init__(self, ecs_client: ECSClient) -> None:
        super().__init__(ecs_client)

    def get_services(self, cluster_name: str) -> list[str]:
        service_arns = paginate_aws_list(self.ecs_client, "list_services", "serviceArns", cluster=cluster_name)
        return [extract_name_from_arn(arn) for arn in service_arns]

    def get_service_info(self, cluster_name: str) -> list[ServiceInfo]:
        service_names = self.get_services(cluster_name)
        if not service_names:
            return []

        response = self.ecs_client.describe_services(cluster=cluster_name, services=service_names)
        services = response.get("services", [])
        return [_create_service_info(service) for service in services]

    def get_desired_task_definition_arn(self, cluster_name: str, service_name: str) -> str | None:
        response = self.ecs_client.describe_services(cluster=cluster_name, services=[service_name])
        services = response.get("services", [])
        if services:
            return services[0].get("taskDefinition")
        return None

    def get_service_events(self, cluster_name: str, service_name: str) -> list[ServiceEvent]:
        response = self.ecs_client.describe_services(cluster=cluster_name, services=[service_name])
        services = response.get("services", [])
        if not services:
            return []

        events = services[0].get("events", [])
        service_events = [_create_service_event(dict(event)) for event in events]

        # Sort by creation time, most recent first (handle None values)
        return sorted(service_events, key=lambda x: x["created_at"] or datetime.min, reverse=True)


def _create_service_info(service: ServiceTypeDef) -> ServiceInfo:
    """Create service info from AWS service description."""
    service_name = service["serviceName"]
    running_count = service.get("runningCount", 0)
    desired_count = service.get("desiredCount", 0)
    pending_count = service.get("pendingCount", 0)

    icon, status = determine_service_status(running_count, desired_count, pending_count)

    display_name = f"{icon} {service_name} ({running_count}/{desired_count})"

    return {
        "name": display_name,
        "status": status,
        "running_count": running_count,
        "desired_count": desired_count,
        "pending_count": pending_count,
    }


def _create_service_event(event: dict[str, Any]) -> ServiceEvent:
    """Create service event from AWS event description."""
    event_id = event.get("id", "")
    created_at = event.get("createdAt")
    message = event.get("message", "")

    event_type = _categorize_event(message)

    return {
        "id": event_id,
        "created_at": created_at,
        "message": message,
        "event_type": event_type,
    }


def _categorize_event(message: str) -> str:
    """Categorize service event based on message content."""
    message_lower = message.lower()

    # Check failure first to catch "deployment failed" as failure, not deployment
    if any(term in message_lower for term in ["failed", "error", "unhealthy", "unable"]):
        return "failure"
    if any(
        term in message_lower
        for term in ["deployment", "deploy", "started", "stopped", "updated", "registered", "deregistered", "targets"]
    ):
        return "deployment"
    if any(
        term in message_lower
        for term in ["scaling", "scale", "capacity", "desired count", "steady state", "running tasks"]
    ):
        return "scaling"
    return "other"
