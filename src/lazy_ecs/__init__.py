import argparse
from typing import TYPE_CHECKING

import boto3
from rich.console import Console

if TYPE_CHECKING:
    from mypy_boto3_ecs import ECSClient

from .aws_service import ECSService
from .core.navigation import handle_navigation, parse_selection
from .core.types import TaskDetails
from .ui import ECSNavigator

console = Console()


def main() -> None:
    """Interactive AWS ECS navigation tool."""
    parser = argparse.ArgumentParser(description="Interactive AWS ECS cluster navigator")
    parser.add_argument("--profile", help="AWS profile to use for authentication", type=str, default=None)
    args = parser.parse_args()

    console.print("🚀 Welcome to lazy-ecs!", style="bold cyan")
    console.print("Interactive AWS ECS cluster navigator\n", style="dim")

    try:
        ecs_client = _create_aws_client(args.profile)
        ecs_service = ECSService(ecs_client)
        navigator = ECSNavigator(ecs_service)

        _navigate_clusters(navigator, ecs_service)

    except Exception as e:
        console.print(f"\n❌ Error: {e}", style="red")
        console.print("Make sure your AWS credentials are configured.", style="dim")


def _create_aws_client(profile_name: str | None) -> "ECSClient":
    """Create AWS ECS client with optional profile support."""
    if profile_name:
        session = boto3.Session(profile_name=profile_name)
        return session.client("ecs")
    return boto3.client("ecs")


def _navigate_clusters(navigator: ECSNavigator, ecs_service: ECSService) -> None:
    """Handle cluster-level navigation with back support."""
    while True:
        selected_cluster = navigator.select_cluster()

        if not selected_cluster:
            console.print("\n❌ No cluster selected. Goodbye!", style="yellow")
            break

        console.print(f"\n✅ Selected cluster: {selected_cluster}", style="green")

        if _navigate_services(navigator, ecs_service, selected_cluster):
            continue  # Back to cluster selection
        break  # Exit was chosen


def _navigate_services(navigator: ECSNavigator, ecs_service: ECSService, cluster_name: str) -> bool:
    """Handle service-level navigation. Returns True if back was chosen, False if exit."""
    service_selection = navigator.select_service(cluster_name)

    # Handle navigation responses (back/exit)
    should_continue, should_exit = handle_navigation(service_selection)
    if not should_continue:
        return not should_exit  # True for back, False for exit

    selection_type, selected_service, _ = parse_selection(service_selection)
    if selection_type != "service":
        return True

    console.print(f"\n✅ Selected service: {selected_service}", style="green")

    while True:
        selection = navigator.select_service_action(cluster_name, selected_service)

        # Handle navigation responses
        should_continue, should_exit = handle_navigation(selection)
        if not should_continue:
            return not should_exit  # True for back, False for exit

        selection_type, action_name, task_arn = parse_selection(selection)
        if selection_type == "task" and action_name == "show_details":
            task_details = ecs_service.get_task_details(cluster_name, selected_service, task_arn)
            if task_details:
                navigator.display_task_details(task_details)
                # Navigate to task features, handle back navigation
                if _handle_task_features(navigator, cluster_name, task_arn, task_details, selected_service):
                    continue  # Back to service selection
                return False  # Exit was chosen
            console.print(f"\n⚠️ Could not fetch task details for {task_arn}", style="yellow")

        elif selection_type == "action" and action_name == "force_deployment":
            navigator.handle_force_deployment(cluster_name, selected_service)
            # Continue the loop to show the menu again


def _handle_task_features(
    navigator: ECSNavigator, cluster_name: str, task_arn: str, task_details: TaskDetails | None, service_name: str
) -> bool:
    """Handle task feature selection and execution. Returns True if back was chosen, False if exit."""
    while True:
        selection = navigator.select_task_feature(task_details)

        # Handle navigation responses
        should_continue, should_exit = handle_navigation(selection)
        if not should_continue:
            return not should_exit  # True for back, False for exit

        selection_type, action_name, container_name = parse_selection(selection)
        if selection_type == "container_action":
            # Map action names to methods
            action_methods = {
                "show_logs": navigator.show_container_logs,
                "show_env": navigator.show_container_environment_variables,
                "show_secrets": navigator.show_container_secrets,
                "show_ports": navigator.show_container_port_mappings,
                "show_volumes": navigator.show_container_volume_mounts,
            }

            if action_name in action_methods:
                action_methods[action_name](cluster_name, task_arn, container_name)

        elif selection_type == "task_action" and action_name == "show_history":
            navigator.show_task_history(cluster_name, service_name)


if __name__ == "__main__":
    main()
