"""Service actions for ECS (deployments, scaling, etc)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...core.base import BaseAWSService

if TYPE_CHECKING:
    from mypy_boto3_ecs.client import ECSClient


class ServiceActions(BaseAWSService):
    """Service actions for ECS services."""

    def __init__(self, ecs_client: ECSClient) -> None:
        super().__init__(ecs_client)

    def force_new_deployment(self, cluster_name: str, service_name: str) -> bool:
        """Force a new deployment for a service."""
        try:
            self.ecs_client.update_service(cluster=cluster_name, service=service_name, forceNewDeployment=True)
            return True
        except Exception:
            return False
