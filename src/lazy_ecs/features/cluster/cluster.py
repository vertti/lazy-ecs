"""Cluster operations for ECS."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...core.base import BaseAWSService
from ...core.utils import extract_name_from_arn, paginate_aws_list

if TYPE_CHECKING:
    from mypy_boto3_ecs.client import ECSClient


class ClusterService(BaseAWSService):
    """Service for ECS cluster operations."""

    def __init__(self, ecs_client: ECSClient) -> None:
        super().__init__(ecs_client)

    def get_cluster_names(self) -> list[str]:
        cluster_arns = paginate_aws_list(self.ecs_client, "list_clusters", "clusterArns")
        return [extract_name_from_arn(arn) for arn in cluster_arns]
