"""Container ports feature."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ....core.base import BaseAWSService
from ....core.context import ContainerContext

if TYPE_CHECKING:
    from mypy_boto3_ecs.client import ECSClient


class PortsFeature(BaseAWSService):
    """Feature for container port operations."""

    def __init__(self, ecs_client: ECSClient) -> None:
        super().__init__(ecs_client)

    def get_port_mappings(self, context: ContainerContext) -> list[dict[str, Any]]:
        """Get port mappings for a container."""
        port_mappings = context.container_definition.get("portMappings", [])
        return [dict(mapping) for mapping in port_mappings]
