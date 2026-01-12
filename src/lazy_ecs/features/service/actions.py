from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypy_boto3_ecs.client import ECSClient


class ServiceActions:
    def __init__(self, ecs_client: ECSClient) -> None:
        self.ecs_client = ecs_client

    def force_new_deployment(self, cluster_name: str, service_name: str) -> bool:
        try:
            self.ecs_client.update_service(cluster=cluster_name, service=service_name, forceNewDeployment=True)
            return True
        except Exception:
            return False
