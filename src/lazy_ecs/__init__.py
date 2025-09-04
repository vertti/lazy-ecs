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
                console.print(f"\n✅ Selected service: {selected_service}", style="green")

                # Navigate to tasks in the selected service
                selected_task = navigator.select_task(selected_cluster, selected_service)

                if selected_task:
                    # Get comprehensive task details
                    task_details = navigator.get_task_details(selected_cluster, selected_service, selected_task)

                    if task_details:
                        console.print("\n✅ Selected Task Details", style="bold green")
                        console.print("=" * 60, style="dim")

                        # Basic task info
                        version_status = "✅ DESIRED" if task_details["is_desired_version"] else "🔴 WRONG VERSION"
                        task_def_name = task_details["task_definition_name"]
                        task_def_revision = task_details["task_definition_revision"]
                        task_def_display = f"{task_def_name}:{task_def_revision}"
                        console.print(f"TASK_DEFINITION: {task_def_display} {version_status}", style="white")
                        console.print(f"TASK_ID: {task_details['task_id'][:16]}...", style="white")
                        console.print(
                            f"STATUS: {task_details['task_status']} | HEALTH: {task_details['health_status']}",
                            style="white",
                        )
                        launch_type = task_details["launch_type"]
                        platform = task_details["platform_version"]
                        launch_info = f"LAUNCH_TYPE: {launch_type} | PLATFORM: {platform}"
                        console.print(launch_info, style="white")

                        # Resource allocation
                        console.print(
                            f"CPU: {task_details['cpu_architecture']} | MEMORY: {task_details['memory']}MB",
                            style="white",
                        )
                        console.print(f"NETWORK: {task_details['network_mode']}", style="white")

                        # Timestamps
                        if task_details.get("created_at"):
                            created_str = task_details["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                            console.print(f"CREATED: {created_str}", style="white")
                        if task_details.get("started_at"):
                            started_str = task_details["started_at"].strftime("%Y-%m-%d %H:%M:%S")
                            console.print(f"STARTED: {started_str}", style="white")

                        # Container details
                        console.print(f"\nCONTAINERS ({len(task_details['containers'])}):", style="bold white")
                        for i, container in enumerate(task_details["containers"], 1):
                            console.print(f"  [{i}] {container['name']}", style="cyan")
                            console.print(f"      IMAGE: {container['image']}", style="white")
                            if container["cpu"]:
                                console.print(f"      CPU: {container['cpu']} units", style="dim")
                            if container["memory"]:
                                console.print(f"      MEMORY: {container['memory']}MB", style="dim")
                            elif container.get("memoryReservation"):
                                console.print(
                                    f"      MEMORY_RESERVATION: {container['memoryReservation']}MB", style="dim"
                                )

                        console.print("=" * 60, style="dim")
                        console.print("🎯 Task selected successfully!", style="blue")
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


if __name__ == "__main__":
    main()
