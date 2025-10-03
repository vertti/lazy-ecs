"""Type definitions for lazy-ecs."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, TypedDict

if TYPE_CHECKING:
    pass


class ServiceInfo(TypedDict):
    name: str
    status: str
    running_count: int
    desired_count: int
    pending_count: int


class TaskInfo(TypedDict):
    name: str
    value: str
    task_def_arn: str
    is_desired: bool
    revision: str
    images: list[str]
    created_at: datetime | None


class TaskDetails(TypedDict):
    task_arn: str
    task_definition_name: str
    task_definition_revision: str
    is_desired_version: bool
    task_status: str
    containers: list[dict[str, Any]]
    created_at: datetime | None
    started_at: datetime | None


class LogConfig(TypedDict):
    log_group: str
    log_stream: str


class ContainerHistoryInfo(TypedDict):
    name: str
    exit_code: int | None
    reason: str | None
    health_status: str | None
    last_status: str


class ServiceEvent(TypedDict):
    id: str
    created_at: datetime | None
    message: str
    event_type: str  # "deployment", "scaling", "failure", "other"


class TaskHistoryDetails(TypedDict):
    task_arn: str
    task_definition_name: str
    task_definition_revision: str
    last_status: str
    desired_status: str
    stop_code: str | None
    stopped_reason: str | None
    created_at: datetime | None
    started_at: datetime | None
    stopped_at: datetime | None
    containers: list[ContainerHistoryInfo]


class MetricStatistics(TypedDict):
    current: float
    average: float
    maximum: float
    minimum: float


class ServiceMetrics(TypedDict):
    cpu: MetricStatistics
    memory: MetricStatistics
