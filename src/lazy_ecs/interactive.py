import questionary
from rich.console import Console

console = Console()


class ECSNavigator:
    def __init__(self, ecs_client):
        self.ecs_client = ecs_client

    def get_cluster_names(self) -> list[str]:
        """Get list of ECS cluster names from AWS."""
        response = self.ecs_client.list_clusters()
        cluster_arns = response.get("clusterArns", [])

        # Extract cluster name from ARN (last part after '/')
        cluster_names = []
        for arn in cluster_arns:
            cluster_name = arn.split("/")[-1]
            cluster_names.append(cluster_name)

        return cluster_names

    def select_cluster(self) -> str:
        """Interactive cluster selection with arrow keys."""
        clusters = self.get_cluster_names()

        if not clusters:
            console.print("No ECS clusters found!", style="red")
            return ""

        selected_cluster = questionary.select(
            "Select an ECS cluster:",
            choices=clusters,
            style=questionary.Style(
                [
                    ("selected", "fg:#61ffca bold"),
                    ("pointer", "fg:#61ffca bold"),
                    ("question", "fg:#ffffff bold"),
                ]
            ),
        ).ask()

        return selected_cluster or ""

    def get_services(self, cluster_name: str) -> list[str]:
        """Get list of ECS service names from specific cluster."""
        response = self.ecs_client.list_services(cluster=cluster_name)
        service_arns = response.get("serviceArns", [])

        service_names = []
        for arn in service_arns:
            service_name = arn.split("/")[-1]
            service_names.append(service_name)

        return service_names

    def get_service_choices(self, cluster_name: str) -> list[dict]:
        """Get services with detailed state information for interactive selection."""
        response = self.ecs_client.list_services(cluster=cluster_name)
        service_arns = response.get("serviceArns", [])

        if not service_arns:
            return []

        # Get detailed service information
        describe_response = self.ecs_client.describe_services(cluster=cluster_name, services=service_arns)
        services = describe_response.get("services", [])

        choices = []
        for service in services:
            service_name = service["serviceName"]
            desired_count = service["desiredCount"]
            running_count = service["runningCount"]
            pending_count = service["pendingCount"]

            # Determine service health status
            if running_count == desired_count and pending_count == 0:
                status_icon = "✅"
                status_text = "HEALTHY"
            elif running_count < desired_count:
                status_icon = "⚠️ "
                status_text = "SCALING"
            elif running_count > desired_count:
                status_icon = "🔄"
                status_text = "DRAINING"
            else:
                status_icon = "❌"
                status_text = "UNHEALTHY"

            # Create display name with state info
            state_info = f"({running_count}/{desired_count})"
            if pending_count > 0:
                state_info = f"({running_count}/{desired_count}, {pending_count} pending)"

            display_name = f"{status_icon} {service_name} {state_info} - {status_text}"

            choices.append(
                {
                    "name": display_name,
                    "value": service_name,
                    "status": status_text,
                    "running_count": running_count,
                    "desired_count": desired_count,
                    "pending_count": pending_count,
                }
            )

        # Sort unhealthy services first
        choices.sort(key=lambda x: (x["status"] == "HEALTHY", x["name"]))
        return choices

    def select_service(self, cluster_name: str) -> str:
        """Interactive service selection with arrow keys and state information."""
        service_choices = self.get_service_choices(cluster_name)

        if not service_choices:
            console.print(f"No services found in cluster '{cluster_name}'!", style="red")
            return ""

        # Show summary of unhealthy services
        unhealthy_services = [s for s in service_choices if s["status"] != "HEALTHY"]
        if unhealthy_services:
            console.print(f"\n⚠️  {len(unhealthy_services)} service(s) not in desired state:", style="bold yellow")
            for service in unhealthy_services:
                console.print(
                    f"  • {service['value']}: {service['running_count']}/{service['desired_count']}", style="yellow"
                )
            console.print()

        selected_service = questionary.select(
            f"Select a service from '{cluster_name}' (unhealthy services shown first):",
            choices=service_choices,
            style=questionary.Style(
                [
                    ("selected", "fg:#61ffca bold"),
                    ("pointer", "fg:#61ffca bold"),
                    ("question", "fg:#ffffff bold"),
                ]
            ),
        ).ask()

        return selected_service or ""

    def get_tasks(self, cluster_name: str, service_name: str) -> list[str]:
        """Get list of running task ARNs for a specific service."""
        response = self.ecs_client.list_tasks(cluster=cluster_name, serviceName=service_name)
        task_arns = response.get("taskArns", [])
        return task_arns

    def select_task(self, cluster_name: str, service_name: str) -> str:
        """Select task - auto-select if single task, interactive if multiple."""
        task_choices = self.get_readable_task_choices(cluster_name, service_name)

        if not task_choices:
            console.print(f"No running tasks found for service '{service_name}'!", style="red")
            return ""

        if len(task_choices) == 1:
            choice = task_choices[0]
            console.print(f"Auto-selected single task: {choice['name']}", style="dim")
            return choice["value"]

        selected_task = questionary.select(
            f"Select a task from '{service_name}':",
            choices=task_choices,
            style=questionary.Style(
                [
                    ("selected", "fg:#61ffca bold"),
                    ("pointer", "fg:#61ffca bold"),
                    ("question", "fg:#ffffff bold"),
                ]
            ),
        ).ask()

        return selected_task or ""

    def get_readable_task_choices(self, cluster_name: str, service_name: str) -> list[dict]:
        """Get list of tasks with human-readable names for interactive selection."""
        task_arns = self.get_tasks(cluster_name, service_name)

        if not task_arns:
            return []

        # Get detailed task information
        response = self.ecs_client.describe_tasks(cluster=cluster_name, tasks=task_arns)
        tasks = response.get("tasks", [])

        choices = []
        for task in tasks:
            task_arn = task["taskArn"]
            task_def_arn = task["taskDefinitionArn"]

            # Extract readable info
            task_def_name = task_def_arn.split("/")[-1].split(":")[0]  # e.g., "web-api-task"
            created_at = task.get("createdAt", "")
            if created_at:
                # Format datetime for readability
                created_str = created_at.strftime("%H:%M:%S")
            else:
                created_str = "unknown"

            # Create human-readable name
            task_id_short = task_arn.split("/")[-1][:8]  # First 8 chars of UUID
            display_name = f"{task_def_name} ({task_id_short}) - {created_str}"

            choices.append({"name": display_name, "value": task_arn})

        # Sort by creation time (newest first)
        choices.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return choices
