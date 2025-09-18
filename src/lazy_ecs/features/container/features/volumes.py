"""Container volumes feature."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ....core.base import BaseAWSService
from ....core.context import ContainerContext

if TYPE_CHECKING:
    from mypy_boto3_ecs.client import ECSClient


class VolumesFeature(BaseAWSService):
    """Feature for container volume operations."""

    def __init__(self, ecs_client: ECSClient) -> None:
        super().__init__(ecs_client)

    def get_volume_mounts(self, context: ContainerContext) -> list[dict[str, Any]]:
        """Get volume mounts for a container."""
        mount_points = context.container_definition.get("mountPoints", [])
        if not mount_points:
            return []

        # Build volume lookup map from task definition volumes
        volumes_map = {}
        for volume in context.task_definition.get("volumes", []):
            volume_name = volume["name"]
            host_config = volume.get("host", {})
            host_path = host_config.get("sourcePath") if host_config else None
            volumes_map[volume_name] = host_path

        # Build volume mounts with resolved host paths
        volume_mounts = []
        for mount_point in mount_points:
            source_volume = mount_point["sourceVolume"]
            host_path = volumes_map.get(source_volume)

            volume_mount = {
                "source_volume": source_volume,
                "container_path": mount_point["containerPath"],
                "read_only": mount_point.get("readOnly", False),
                "host_path": host_path,
            }
            volume_mounts.append(volume_mount)

        return volume_mounts
