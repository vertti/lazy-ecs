from __future__ import annotations


def build_cluster_url(region: str, cluster_name: str) -> str:
    return f"https://{region}.console.aws.amazon.com/ecs/v2/clusters/{cluster_name}"


def build_service_url(region: str, cluster_name: str, service_name: str) -> str:
    return f"https://{region}.console.aws.amazon.com/ecs/v2/clusters/{cluster_name}/services/{service_name}"


def build_task_url(region: str, cluster_name: str, task_arn: str) -> str:
    task_id = _extract_task_id(task_arn)
    return f"https://{region}.console.aws.amazon.com/ecs/v2/clusters/{cluster_name}/tasks/{task_id}"


def _extract_task_id(task_arn: str) -> str:
    if task_arn.startswith("arn:aws:ecs:"):
        return task_arn.rsplit("/", maxsplit=1)[-1]
    return task_arn
