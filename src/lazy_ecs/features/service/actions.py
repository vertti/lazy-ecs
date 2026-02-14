from __future__ import annotations

from typing import TYPE_CHECKING

from botocore.exceptions import BotoCoreError, ClientError

if TYPE_CHECKING:
    from mypy_boto3_ecs.client import ECSClient


class ServiceActions:
    def __init__(self, ecs_client: ECSClient) -> None:
        self.ecs_client = ecs_client

    def force_new_deployment(self, cluster_name: str, service_name: str) -> tuple[bool, str | None]:
        try:
            self.ecs_client.update_service(cluster=cluster_name, service=service_name, forceNewDeployment=True)
            return True, None
        except ClientError as e:
            error = e.response.get("Error", {})
            code = error.get("Code")
            message = error.get("Message", str(e))
            error_message = f"{code}: {message}" if code else message
            return False, error_message
        except BotoCoreError as e:
            return False, str(e)
