import boto3
from rich.console import Console

from .aws_service import ECSService, TaskDetails
from .ui import ECSNavigator

console = Console()


def main() -> None:
    """Interactive AWS ECS navigation tool."""
    console.print("🚀 Welcome to lazy-ecs!", style="bold cyan")
    console.print("Interactive AWS ECS cluster navigator\n", style="dim")

    try:
        # Initialize AWS ECS client and service layer
        ecs_client = boto3.client("ecs")
        ecs_service = ECSService(ecs_client)
        navigator = ECSNavigator(ecs_service)

        # Start interactive navigation
        selected_cluster = navigator.select_cluster()

        if selected_cluster:
            console.print(f"\n✅ Selected cluster: {selected_cluster}", style="green")

            # Navigate to services in the selected cluster
            selected_service = navigator.select_service(selected_cluster)

            if selected_service:
                console.print(f"\n✅ Selected service: {selected_service}", style="green")

                # Navigate to tasks in the selected service
                selected_task = navigator.select_task(selected_cluster, selected_service)

                if selected_task:
                    task_details = ecs_service.get_task_details(selected_cluster, selected_service, selected_task)
                    if task_details:
                        navigator.display_task_details(task_details)
                        _handle_task_features(navigator, selected_cluster, selected_task, task_details)
                    else:
                        console.print(f"\n⚠️ Could not fetch task details for {selected_task}", style="yellow")
                else:
                    console.print(
                        f"\n❌ No task selected from '{selected_service}'. Goodbye!",
                        style="yellow",
                    )
            else:
                console.print(
                    f"\n❌ No service selected from '{selected_cluster}'. Goodbye!",
                    style="yellow",
                )
        else:
            console.print("\n❌ No cluster selected. Goodbye!", style="yellow")

    except Exception as e:
        console.print(f"\n❌ Error: {e}", style="red")
        console.print("Make sure your AWS credentials are configured.", style="dim")


def _handle_task_features(
    navigator: ECSNavigator, cluster_name: str, task_arn: str, task_details: TaskDetails | None
) -> None:
    """Handle task feature selection and execution."""
    while True:
        selected_feature = navigator.select_task_feature(task_details)

        if not selected_feature or selected_feature == "Exit":
            console.print("\n👋 Goodbye!", style="cyan")
            break

        # Map feature prefixes to their corresponding methods
        feature_actions = {
            "Show tail of logs for container:": navigator.show_container_logs,
            "Show environment variables for container:": navigator.show_container_environment_variables,
            "Show secrets for container:": navigator.show_container_secrets,
            "Show port mappings for container:": navigator.show_container_port_mappings,
        }

        for prefix, action in feature_actions.items():
            if selected_feature.startswith(prefix):
                container_name = _extract_container_name(selected_feature)
                action(cluster_name, task_arn, container_name)
                break


def _extract_container_name(feature_text: str) -> str:
    """Extract container name from feature selection text."""
    return feature_text.split("container: ")[-1]


if __name__ == "__main__":
    main()
