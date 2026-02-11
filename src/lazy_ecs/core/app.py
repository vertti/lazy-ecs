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
    while True:
        selected_cluster = navigator.select_cluster()

        if not selected_cluster:
            console.print("\n❌ No cluster selected. Goodbye!", style="yellow")
            break

        console.print(f"\n✅ Selected cluster: {selected_cluster}", style="green")

        while True:
            cluster_action = navigator.select_cluster_action(selected_cluster)

            should_continue, should_exit = handle_navigation(cluster_action)
            if not should_continue:
                if should_exit:
                    return
                break

            selection_type, action_name, cluster_name = parse_selection(cluster_action)
            if selection_type != "cluster_action":
                continue

            if action_name == "browse_services":
                if navigate_services(navigator, ecs_service, cluster_name):
                    break
                return

            dispatch_cluster_action(navigator, cluster_name, action_name)


def dispatch_cluster_action(navigator: ECSNavigator, cluster_name: str, action_name: str) -> None:
    cluster_actions = get_cluster_action_handlers()
    if action_name in cluster_actions:
        cluster_actions[action_name](navigator, cluster_name)


def navigate_services(navigator: ECSNavigator, ecs_service: ECSService, cluster_name: str) -> bool:
    """Returns True if back was chosen, False if exit."""
    service_selection = navigator.select_service(cluster_name)

    should_continue, should_exit = handle_navigation(service_selection)
    if not should_continue:
        return not should_exit  # True for back, False for exit

    selection_type, selected_service, _ = parse_selection(service_selection)
    if selection_type != "service":
        return True

    console.print(f"\n✅ Selected service: {selected_service}", style="green")

    while True:
        selection = navigator.select_service_action(cluster_name, selected_service)

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
    """Returns True if back was chosen, False if exit."""
    with show_spinner():
        task_details = ecs_service.get_task_details(cluster_name, service_name, task_arn)

    if not task_details:
        console.print(f"\n⚠️ Could not fetch task details for {task_arn}", style="yellow")
        return True

    navigator.display_task_details(task_details)
    return handle_task_features(navigator, cluster_name, task_arn, task_details, service_name)


def dispatch_service_action(navigator: ECSNavigator, cluster_name: str, service_name: str, action_name: str) -> None:
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
    """Returns True if back was chosen, False if exit."""
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
    task_actions = get_task_action_handlers()
    if action_name in task_actions:
        task_actions[action_name](navigator, cluster_name, service_name, task_arn, task_details)
        return True
    return False


def get_container_action_handlers() -> dict[str, "Callable"]:
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


def get_cluster_action_handlers() -> dict[str, "Callable"]:
    return {
        "open_console": lambda nav, cluster: nav.open_cluster_in_console(cluster),
    }


def get_task_action_handlers() -> dict[str, "Callable"]:
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
        "stop_task": lambda nav, cluster, service, task_arn, _task_details: nav.handle_stop_task(
            cluster, task_arn, service
        ),
    }


def get_service_action_handlers() -> dict[str, "Callable"]:
    return {
        "force_deployment": lambda nav, cluster, service: nav.handle_force_deployment(cluster, service),
        "show_events": lambda nav, cluster, service: nav.show_service_events(cluster, service),
        "show_metrics": lambda nav, cluster, service: nav.show_service_metrics(cluster, service),
        "open_console": lambda nav, cluster, service: nav.open_service_in_console(cluster, service),
    }
