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

    def select_service(self, cluster_name: str) -> str:
        """Interactive service selection with arrow keys."""
        services = self.get_services(cluster_name)

        if not services:
            console.print(f"No services found in cluster '{cluster_name}'!", style="red")
            return ""

        selected_service = questionary.select(
            f"Select a service from '{cluster_name}':",
            choices=services,
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

        # Return task IDs (last part of ARN) for easier display
        task_ids = []
        for arn in task_arns:
            task_id = arn.split("/")[-1]
            task_ids.append(task_id)

        return task_ids

    def select_task(self, cluster_name: str, service_name: str) -> str:
        """Select task - auto-select if single task, interactive if multiple."""
        tasks = self.get_tasks(cluster_name, service_name)

        if not tasks:
            console.print(f"No running tasks found for service '{service_name}'!", style="red")
            return ""

        if len(tasks) == 1:
            task_id = tasks[0]
            console.print(f"Auto-selected single task: {task_id}", style="dim")
            return task_id

        selected_task = questionary.select(
            f"Select a task from '{service_name}':",
            choices=tasks,
            style=questionary.Style(
                [
                    ("selected", "fg:#61ffca bold"),
                    ("pointer", "fg:#61ffca bold"),
                    ("question", "fg:#ffffff bold"),
                ]
            ),
        ).ask()

        return selected_task or ""
