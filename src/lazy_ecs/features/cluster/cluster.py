from __future__ import annotations

from typing import TYPE_CHECKING

from ...core.utils import extract_name_from_arn, paginate_aws_list

if TYPE_CHECKING:
    from mypy_boto3_ecs.client import ECSClient


class ClusterService:
    def __init__(self, ecs_client: ECSClient) -> None:
        self.ecs_client = ecs_client

    def get_cluster_names(self) -> list[str]:
        cluster_arns = paginate_aws_list(self.ecs_client, "list_clusters", "clusterArns")
        return [extract_name_from_arn(arn) for arn in cluster_arns]
