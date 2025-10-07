import argparse
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING

import boto3
from botocore.config import Config
from rich.console import Console

if TYPE_CHECKING:
    from mypy_boto3_cloudwatch.client import CloudWatchClient
    from mypy_boto3_ecs import ECSClient
    from mypy_boto3_logs.client import CloudWatchLogsClient
    from mypy_boto3_sts.client import STSClient

from .aws_service import ECSService
from .core.app import navigate_clusters
from .ui import ECSNavigator

try:
    __version__ = version("lazy-ecs")
except PackageNotFoundError:
    __version__ = "dev"

console = Console()


def main() -> None:
    """Interactive AWS ECS navigation tool."""
    parser = argparse.ArgumentParser(description="Interactive AWS ECS cluster navigator")
    parser.add_argument("--version", action="version", version=f"lazy-ecs {__version__}")
    parser.add_argument("--profile", help="AWS profile to use for authentication", type=str, default=None)
    args = parser.parse_args()

    console.print("🚀 Welcome to lazy-ecs!", style="bold cyan")
    console.print("Interactive AWS ECS cluster navigator\n", style="dim")

    try:
        ecs_client = _create_aws_client(args.profile)
        logs_client = _create_logs_client(args.profile)
        sts_client = _create_sts_client(args.profile)
        cloudwatch_client = _create_cloudwatch_client(args.profile)
        ecs_service = ECSService(ecs_client, sts_client, logs_client, cloudwatch_client)
        navigator = ECSNavigator(ecs_service)

        navigate_clusters(navigator, ecs_service)

    except Exception as e:
        console.print(f"\n❌ Error: {e}", style="red")
        console.print("Make sure your AWS credentials are configured.", style="dim")


def _create_aws_client(profile_name: str | None) -> "ECSClient":
    """Create optimized AWS ECS client with connection pooling."""
    config = Config(
        max_pool_connections=5,
        retries={"max_attempts": 2, "mode": "adaptive"},
    )

    session = boto3.Session(profile_name=profile_name) if profile_name else boto3
    return session.client("ecs", config=config)


def _create_logs_client(profile_name: str | None) -> "CloudWatchLogsClient":
    """Create optimized CloudWatch Logs client with connection pooling."""
    config = Config(
        max_pool_connections=5,
        retries={"max_attempts": 2, "mode": "adaptive"},
    )

    session = boto3.Session(profile_name=profile_name) if profile_name else boto3
    return session.client("logs", config=config)


def _create_sts_client(profile_name: str | None) -> "STSClient":
    """Create optimized STS client with connection pooling."""
    config = Config(
        max_pool_connections=5,
        retries={"max_attempts": 2, "mode": "adaptive"},
    )

    session = boto3.Session(profile_name=profile_name) if profile_name else boto3
    return session.client("sts", config=config)


def _create_cloudwatch_client(profile_name: str | None) -> "CloudWatchClient":
    """Create optimized CloudWatch client with connection pooling."""
    config = Config(
        max_pool_connections=5,
        retries={"max_attempts": 2, "mode": "adaptive"},
    )

    session = boto3.Session(profile_name=profile_name) if profile_name else boto3
    return session.client("cloudwatch", config=config)


if __name__ == "__main__":
    main()
