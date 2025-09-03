import boto3
from rich.console import Console

from .interactive import ECSNavigator

console = Console()


def main() -> None:
    """Interactive AWS ECS navigation tool."""
    console.print("🚀 Welcome to lazy-ecs!", style="bold cyan")
    console.print("Interactive AWS ECS cluster navigator\n", style="dim")

    try:
        # Initialize AWS ECS client
        ecs_client = boto3.client("ecs")
        navigator = ECSNavigator(ecs_client)

        # Start interactive navigation
        selected_cluster = navigator.select_cluster()

        if selected_cluster:
            console.print(f"\n✅ Selected cluster: {selected_cluster}", style="green")

            # Navigate to services in the selected cluster
            selected_service = navigator.select_service(selected_cluster)

            if selected_service:
                console.print(
                    f"\n✅ Selected service: {selected_service}", style="green"
                )

                # Navigate to tasks in the selected service
                selected_task = navigator.select_task(
                    selected_cluster, selected_service
                )

                if selected_task:
                    console.print(f"\n✅ Selected task: {selected_task}", style="green")
                    console.print(
                        f"🎯 Task '{selected_task}' in service '{selected_service}'",
                        style="blue",
                    )
                    console.print(f"   Cluster: {selected_cluster}", style="dim")
                    # TODO: Show task details, logs, etc.
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


if __name__ == "__main__":
    main()
