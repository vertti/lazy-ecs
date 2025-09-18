"""Container environment and secrets feature."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ....core.base import BaseAWSService
from ....core.context import ContainerContext

if TYPE_CHECKING:
    from mypy_boto3_ecs.client import ECSClient


class EnvironmentFeature(BaseAWSService):
    """Feature for container environment variables and secrets."""

    def __init__(self, ecs_client: ECSClient) -> None:
        super().__init__(ecs_client)

    def get_environment_variables(self, context: ContainerContext) -> dict[str, str]:
        """Get environment variables for a container."""
        environment = context.container_definition.get("environment", [])
        return {env_var["name"]: env_var["value"] for env_var in environment}

    def get_secrets(self, context: ContainerContext) -> dict[str, str]:
        """Get secrets configuration for a container."""
        secrets = context.container_definition.get("secrets", [])
        return {secret["name"]: secret["valueFrom"] for secret in secrets}
