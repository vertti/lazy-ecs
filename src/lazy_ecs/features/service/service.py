"""Service operations for ECS."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...core.base import BaseAWSService
from ...core.types import ServiceInfo
from ...core.utils import determine_service_status, extract_name_from_arn

if TYPE_CHECKING:
    from mypy_boto3_ecs.client import ECSClient
    from mypy_boto3_ecs.type_defs import ServiceTypeDef


class ServiceService(BaseAWSService):
    """Service for ECS service operations."""

    def __init__(self, ecs_client: ECSClient) -> None:
        super().__init__(ecs_client)

    def get_services(self, cluster_name: str) -> list[str]:
        """Get list of service names in a cluster."""
        response = self.ecs_client.list_services(cluster=cluster_name)
        service_arns = response.get("serviceArns", [])
        return [extract_name_from_arn(arn) for arn in service_arns]

    def get_service_info(self, cluster_name: str) -> list[ServiceInfo]:
        """Get detailed service information with status."""
        service_names = self.get_services(cluster_name)
        if not service_names:
            return []

        response = self.ecs_client.describe_services(cluster=cluster_name, services=service_names)
        services = response.get("services", [])
        return [_create_service_info(service) for service in services]

    def get_desired_task_definition_arn(self, cluster_name: str, service_name: str) -> str | None:
        """Get the desired task definition ARN for a service."""
        response = self.ecs_client.describe_services(cluster=cluster_name, services=[service_name])
        services = response.get("services", [])
        if services:
            return services[0].get("taskDefinition")
        return None


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
