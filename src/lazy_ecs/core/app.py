"""Main application logic for lazy-ecs CLI."""

from typing import TYPE_CHECKING

from rich.console import Console

from ..aws_service import ECSService
from ..core.navigation import handle_navigation, parse_selection
from ..core.types import TaskDetails
from ..core.utils import show_spinner
from ..ui import ECSNavigator

if TYPE_CHECKING:
    from collections.abc import Callable

console = Console()


def navigate_clusters(navigator: ECSNavigator, ecs_service: ECSService) -> None:
    """Handle cluster-level navigation with back support."""
    while True:
        selected_cluster = navigator.select_cluster()

        if not selected_cluster:
            console.print("\n❌ No cluster selected. Goodbye!", style="yellow")
            break

        console.print(f"\n✅ Selected cluster: {selected_cluster}", style="green")

        if navigate_services(navigator, ecs_service, selected_cluster):
            continue  # Back to cluster selection
        break  # Exit was chosen


def navigate_services(navigator: ECSNavigator, ecs_service: ECSService, cluster_name: str) -> bool:
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
            if not handle_task_selection(navigator, ecs_service, cluster_name, selected_service, task_arn):
                return False  # Exit was chosen
            continue  # Back to service selection

        if selection_type == "action":
            dispatch_service_action(navigator, cluster_name, selected_service, action_name)


def handle_task_selection(
    navigator: ECSNavigator,
    ecs_service: ECSService,
    cluster_name: str,
    service_name: str,
    task_arn: str,
) -> bool:
    """Handle task selection and navigation. Returns True if back was chosen, False if exit."""
    with show_spinner():
        task_details = ecs_service.get_task_details(cluster_name, service_name, task_arn)

    if not task_details:
        console.print(f"\n⚠️ Could not fetch task details for {task_arn}", style="yellow")
        return True

    navigator.display_task_details(task_details)
    return handle_task_features(navigator, cluster_name, task_arn, task_details, service_name)


def dispatch_service_action(navigator: ECSNavigator, cluster_name: str, service_name: str, action_name: str) -> None:
    """Dispatch service action to appropriate handler."""
    service_actions = get_service_action_handlers()
    if action_name in service_actions:
        service_actions[action_name](navigator, cluster_name, service_name)


def handle_task_features(
    navigator: ECSNavigator,
    cluster_name: str,
    task_arn: str,
    task_details: TaskDetails | None,
    service_name: str,
) -> bool:
    """Handle task feature selection and execution. Returns True if back was chosen, False if exit."""
    while True:
        selection = navigator.select_task_feature(task_details)

        should_continue, should_exit = handle_navigation(selection)
        if not should_continue:
            return not should_exit

        selection_type, action_name, container_name = parse_selection(selection)

        if selection_type == "container_action":
            dispatch_container_action(navigator, cluster_name, task_arn, container_name, action_name)
        elif selection_type == "task_action":
            dispatch_task_action(navigator, cluster_name, service_name, task_arn, task_details, action_name)


def dispatch_container_action(
    navigator: ECSNavigator,
    cluster_name: str,
    task_arn: str,
    container_name: str,
    action_name: str,
) -> bool:
    """Dispatch container action to appropriate handler. Returns True if action was found and executed."""
    container_actions = get_container_action_handlers()
    if action_name in container_actions:
        container_actions[action_name](navigator, cluster_name, task_arn, container_name)
        return True
    return False


def dispatch_task_action(
    navigator: ECSNavigator,
    cluster_name: str,
    service_name: str,
    task_arn: str,
    task_details: TaskDetails | None,
    action_name: str,
) -> bool:
    """Dispatch task action to appropriate handler. Returns True if action was found and executed."""
    task_actions = get_task_action_handlers()
    if action_name in task_actions:
        task_actions[action_name](navigator, cluster_name, service_name, task_arn, task_details)
        return True
    return False


def get_container_action_handlers() -> dict[str, "Callable"]:
    """Get mapping of container action names to their handlers."""
    return {
        "tail_logs": lambda nav, cluster, task_arn, container: nav.show_container_logs_live_tail(
            cluster,
            task_arn,
            container,
        ),
        "show_env": lambda nav, cluster, task_arn, container: nav.show_container_environment_variables(
            cluster,
            task_arn,
            container,
        ),
        "show_secrets": lambda nav, cluster, task_arn, container: nav.show_container_secrets(
            cluster, task_arn, container
        ),
        "show_ports": lambda nav, cluster, task_arn, container: nav.show_container_port_mappings(
            cluster,
            task_arn,
            container,
        ),
        "show_volumes": lambda nav, cluster, task_arn, container: nav.show_container_volume_mounts(
            cluster,
            task_arn,
            container,
        ),
    }


def get_task_action_handlers() -> dict[str, "Callable"]:
    """Get mapping of task action names to their handlers."""
    return {
        "show_history": lambda nav, cluster, service, _task_arn, _task_details: nav.show_task_history(cluster, service),
        "show_details": lambda nav, _cluster, _service, _task_arn, task_details: nav.display_task_details(task_details),
        "compare_definitions": lambda nav,
        _cluster,
        _service,
        _task_arn,
        task_details: nav.show_task_definition_comparison(
            task_details,
        ),
        "open_console": lambda nav, cluster, _service, task_arn, _task_details: nav.open_task_in_console(
            cluster, task_arn
        ),
    }


def get_service_action_handlers() -> dict[str, "Callable"]:
    """Get mapping of service action names to their handlers."""
    return {
        "force_deployment": lambda nav, cluster, service: nav.handle_force_deployment(cluster, service),
        "show_events": lambda nav, cluster, service: nav.show_service_events(cluster, service),
        "show_metrics": lambda nav, cluster, service: nav.show_service_metrics(cluster, service),
        "open_console": lambda nav, cluster, service: nav.open_service_in_console(cluster, service),
    }
