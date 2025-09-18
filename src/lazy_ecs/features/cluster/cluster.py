"""Cluster operations for ECS."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...core.base import BaseAWSService
from ...core.utils import extract_name_from_arn

if TYPE_CHECKING:
    from mypy_boto3_ecs.client import ECSClient


class ClusterService(BaseAWSService):
    """Service for ECS cluster operations."""

    def __init__(self, ecs_client: ECSClient) -> None:
        super().__init__(ecs_client)

    def get_cluster_names(self) -> list[str]:
        """Get list of ECS cluster names from AWS."""
        response = self.ecs_client.list_clusters()
        cluster_arns = response.get("clusterArns", [])
        return [extract_name_from_arn(arn) for arn in cluster_arns]
