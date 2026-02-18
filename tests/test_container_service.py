"""Tests for container service functions."""

from unittest.mock import Mock, call

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from lazy_ecs.features.container.container import (
    ContainerService,
    LiveTailError,
    build_log_group_arn,
    build_log_stream_name,
)


@pytest.fixture
def mock_task_service():
    return Mock()


@pytest.fixture
def container_service(mock_task_service):
    mock_ecs_client = Mock()
    return ContainerService(mock_ecs_client, mock_task_service)


@pytest.fixture
def make_live_tail_service(mock_task_service):
    def _make_live_tail_service(
        *,
        region: str | None = "us-east-1",
        logs_client: Mock | None = None,
        sts_client: Mock | None = None,
        use_sts: bool = True,
        default_account_id: str = "123456789012",
    ) -> tuple[ContainerService, Mock, Mock | None, Mock]:
        mock_ecs_client = Mock()
        mock_ecs_client.meta.region_name = region

        resolved_logs_client = logs_client if logs_client is not None else Mock()

        if use_sts:
            resolved_sts_client = sts_client if sts_client is not None else Mock()
            if sts_client is None:
                resolved_sts_client.get_caller_identity.return_value = {"Account": default_account_id}
        else:
            resolved_sts_client = None

        service = ContainerService(
            mock_ecs_client,
            mock_task_service,
            sts_client=resolved_sts_client,
            logs_client=resolved_logs_client,
        )
        return service, mock_ecs_client, resolved_sts_client, resolved_logs_client

    return _make_live_tail_service


@pytest.fixture
def mock_task_with_awslogs():
    return {
        "taskArn": "arn:aws:ecs:us-east-1:123:task/cluster/abc123",
        "taskDefinitionArn": "arn:task-def:1",
    }


@pytest.fixture
def mock_task_definition_with_awslogs():
    return {
        "containerDefinitions": [
            {
                "name": "web",
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {"awslogs-group": "/ecs/my-app"},
                },
            }
        ]
    }


def test_get_container_context_returns_none_when_task_not_found(container_service, mock_task_service):
    mock_task_service.get_task_and_definition.return_value = None

    result = container_service.get_container_context("cluster", "task-arn", "container-name")

    assert result is None


def test_get_container_context_returns_none_when_container_not_found(container_service, mock_task_service):
    mock_task = {"taskArn": "task-arn"}
    mock_task_definition = {
        "containerDefinitions": [
            {"name": "other-container", "image": "nginx:latest"},
        ]
    }
    mock_task_service.get_task_and_definition.return_value = (mock_task, mock_task_definition)

    result = container_service.get_container_context("cluster", "task-arn", "missing-container")

    assert result is None


def test_get_container_context_success(container_service, mock_task_service):
    mock_task = {"taskArn": "task-arn"}
    mock_task_definition = {
        "containerDefinitions": [
            {"name": "web", "image": "nginx:latest"},
        ]
    }
    mock_task_service.get_task_and_definition.return_value = (mock_task, mock_task_definition)

    result = container_service.get_container_context("cluster", "task-arn", "web")

    assert result.container_name == "web"
    assert result.cluster_name == "cluster"
    assert result.task_arn == "task-arn"


def test_get_container_definition_not_found(container_service):
    task_definition = {
        "containerDefinitions": [
            {"name": "web", "image": "nginx:latest"},
        ]
    }

    result = container_service.get_container_definition(task_definition, "missing")

    assert result is None


def test_get_container_definition_success(container_service):
    task_definition = {
        "containerDefinitions": [
            {"name": "web", "image": "nginx:latest"},
            {"name": "worker", "image": "python:3.11"},
        ]
    }

    result = container_service.get_container_definition(task_definition, "worker")

    assert result["name"] == "worker"
    assert result["image"] == "python:3.11"


def test_build_log_group_arn():
    arn = build_log_group_arn("us-east-1", "123456789012", "my-log-group")

    assert arn == "arn:aws:logs:us-east-1:123456789012:log-group:my-log-group"


def test_build_log_stream_name():
    stream = build_log_stream_name("ecs", "web-container", "abc123def456")

    assert stream == "ecs/web-container/abc123def456"


def test_build_log_stream_name_with_custom_prefix():
    stream = build_log_stream_name("my-app", "worker", "task-id-123")

    assert stream == "my-app/worker/task-id-123"


def test_get_log_config_returns_none_when_context_not_found(container_service, mock_task_service):
    mock_task_service.get_task_and_definition.return_value = None

    result = container_service.get_log_config("cluster", "task-arn", "container")

    assert result is None


def test_get_log_config_returns_none_for_non_awslogs_driver(
    container_service, mock_task_service, mock_task_with_awslogs
):
    mock_task_definition = {"containerDefinitions": [{"name": "web", "logConfiguration": {"logDriver": "splunk"}}]}
    mock_task_service.get_task_and_definition.return_value = (mock_task_with_awslogs, mock_task_definition)

    result = container_service.get_log_config("cluster", "task-arn", "web")

    assert result is None


def test_get_log_config_returns_none_when_no_log_group(container_service, mock_task_service, mock_task_with_awslogs):
    mock_task_definition = {
        "containerDefinitions": [{"name": "web", "logConfiguration": {"logDriver": "awslogs", "options": {}}}]
    }
    mock_task_service.get_task_and_definition.return_value = (mock_task_with_awslogs, mock_task_definition)

    result = container_service.get_log_config("cluster", "task-arn", "web")

    assert result is None


def test_get_log_config_success_with_defaults(
    container_service, mock_task_service, mock_task_with_awslogs, mock_task_definition_with_awslogs
):
    mock_task_service.get_task_and_definition.return_value = (mock_task_with_awslogs, mock_task_definition_with_awslogs)

    result = container_service.get_log_config("cluster", "arn:aws:ecs:us-east-1:123:task/cluster/abc123", "web")

    assert result["log_group"] == "/ecs/my-app"
    assert result["log_stream"] == "ecs/web/abc123"


def test_get_log_config_success_with_custom_prefix(container_service, mock_task_service):
    mock_task = {"taskArn": "arn:aws:ecs:us-east-1:123:task/cluster/task-id-456"}
    mock_task_definition = {
        "containerDefinitions": [
            {
                "name": "worker",
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {"awslogs-group": "/ecs/workers", "awslogs-stream-prefix": "app"},
                },
            }
        ]
    }
    mock_task_service.get_task_and_definition.return_value = (mock_task, mock_task_definition)

    result = container_service.get_log_config("cluster", "arn:aws:ecs:us-east-1:123:task/cluster/task-id-456", "worker")

    assert result["log_group"] == "/ecs/workers"
    assert result["log_stream"] == "app/worker/task-id-456"


def test_get_container_logs_returns_empty_when_no_client(mock_task_service):
    container_service = ContainerService(Mock(), mock_task_service, logs_client=None)

    result = container_service.get_container_logs("/ecs/app", "stream")

    assert result == []


def test_get_container_logs_success():
    mock_logs_client = Mock()
    mock_logs_client.get_log_events.return_value = {"events": [{"message": "log1"}, {"message": "log2"}]}
    container_service = ContainerService(Mock(), Mock(), logs_client=mock_logs_client)

    result = container_service.get_container_logs("/ecs/app", "stream", lines=100)

    assert len(result) == 2
    mock_logs_client.get_log_events.assert_called_once_with(
        logGroupName="/ecs/app", logStreamName="stream", limit=100, startFromHead=False
    )


def test_get_container_logs_filtered_returns_empty_when_no_client(mock_task_service):
    container_service = ContainerService(Mock(), mock_task_service, logs_client=None)

    result = container_service.get_container_logs_filtered("/ecs/app", "stream", "ERROR")

    assert result == []


def test_get_container_logs_filtered_success():
    mock_logs_client = Mock()
    mock_logs_client.filter_log_events.return_value = {"events": [{"message": "ERROR: failed"}]}
    container_service = ContainerService(Mock(), Mock(), logs_client=mock_logs_client)

    result = container_service.get_container_logs_filtered("/ecs/app", "stream", "ERROR", lines=25)

    assert len(result) == 1
    mock_logs_client.filter_log_events.assert_called_once_with(
        logGroupName="/ecs/app", logStreamNames=["stream"], filterPattern="ERROR", limit=25
    )


def test_get_live_container_logs_tail_raises_when_logs_client_missing(mock_task_service):
    mock_ecs_client = Mock()
    mock_ecs_client.meta.region_name = "us-east-1"
    container_service = ContainerService(mock_ecs_client, mock_task_service, logs_client=None)

    with pytest.raises(LiveTailError, match="CloudWatch Logs client is not configured"):
        list(container_service.get_live_container_logs_tail("/ecs/app", "stream"))


def test_get_live_container_logs_tail_raises_when_account_id_missing(make_live_tail_service):
    container_service, _, _, _ = make_live_tail_service(use_sts=False)

    with pytest.raises(LiveTailError, match="AWS account ID is required for live tail"):
        list(container_service.get_live_container_logs_tail("/ecs/app", "stream", aws_account_id=""))


def test_get_live_container_logs_tail_raises_when_region_missing(make_live_tail_service):
    container_service, _, _, _ = make_live_tail_service(region=None)

    with pytest.raises(LiveTailError, match="AWS region is not configured for ECS client"):
        list(container_service.get_live_container_logs_tail("/ecs/app", "stream"))


def test_get_live_container_logs_tail_raises_actionable_sts_client_error(make_live_tail_service):
    mock_sts_client = Mock()
    mock_sts_client.get_caller_identity.side_effect = ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "Not allowed"}},
        "GetCallerIdentity",
    )
    container_service, _, _, _ = make_live_tail_service(sts_client=mock_sts_client)

    with pytest.raises(
        LiveTailError, match="Failed to get AWS account ID from STS: AccessDeniedException: Not allowed"
    ):
        list(container_service.get_live_container_logs_tail("/ecs/app", "stream"))


def test_get_live_container_logs_tail_raises_actionable_sts_botocore_error(make_live_tail_service):
    mock_sts_client = Mock()
    mock_sts_client.get_caller_identity.side_effect = EndpointConnectionError(endpoint_url="https://sts.amazonaws.com")
    container_service, _, _, _ = make_live_tail_service(sts_client=mock_sts_client)

    with pytest.raises(LiveTailError, match="Failed to get AWS account ID from STS"):
        list(container_service.get_live_container_logs_tail("/ecs/app", "stream"))


def test_get_live_container_logs_tail_raises_actionable_client_error(make_live_tail_service):
    mock_logs_client = Mock()
    mock_logs_client.start_live_tail.side_effect = ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "Not authorized"}},
        "StartLiveTail",
    )
    container_service, _, _, _ = make_live_tail_service(logs_client=mock_logs_client)

    with pytest.raises(LiveTailError, match="AccessDeniedException: Not authorized"):
        list(container_service.get_live_container_logs_tail("/ecs/app", "stream"))


def test_get_live_container_logs_tail_raises_actionable_start_live_tail_botocore_error(make_live_tail_service):
    mock_logs_client = Mock()
    mock_logs_client.start_live_tail.side_effect = EndpointConnectionError(
        endpoint_url="https://logs.us-east-1.amazonaws.com",
    )
    container_service, _, _, _ = make_live_tail_service(logs_client=mock_logs_client)

    with pytest.raises(LiveTailError, match="Failed to start CloudWatch live tail"):
        list(container_service.get_live_container_logs_tail("/ecs/app", "stream"))


def test_get_live_container_logs_tail_raises_when_response_stream_missing(make_live_tail_service):
    mock_logs_client = Mock()
    mock_logs_client.start_live_tail.return_value = {}
    container_service, _, _, _ = make_live_tail_service(logs_client=mock_logs_client)

    with pytest.raises(LiveTailError, match="did not return a response stream"):
        list(container_service.get_live_container_logs_tail("/ecs/app", "stream"))


def test_get_live_container_logs_tail_yields_session_results_and_closes_stream(make_live_tail_service):
    stream_event = {"eventId": "evt-1", "timestamp": 1234, "message": "from-stream"}
    update_event = {"eventId": "evt-2", "timestamp": 1235, "message": "from-update"}

    mock_response_stream = Mock()
    mock_response_stream.__iter__ = Mock(
        return_value=iter(
            [
                {"sessionStart": {"requestId": "abc"}},
                {"sessionUpdate": {"sessionResults": [update_event]}},
                stream_event,
            ],
        ),
    )
    mock_logs_client = Mock()
    mock_logs_client.start_live_tail.return_value = {"responseStream": mock_response_stream}

    container_service, _, _, _ = make_live_tail_service(logs_client=mock_logs_client)

    results = list(container_service.get_live_container_logs_tail("/ecs/app", "stream"))

    assert results == [update_event, stream_event]
    mock_response_stream.close.assert_called_once()


def test_get_live_container_logs_tail_uses_explicit_account_id_without_sts_lookup(make_live_tail_service):
    mock_response_stream = Mock()
    mock_response_stream.__iter__ = Mock(return_value=iter([]))

    mock_logs_client = Mock()
    mock_logs_client.start_live_tail.return_value = {"responseStream": mock_response_stream}

    mock_sts_client = Mock()
    mock_sts_client.get_caller_identity.side_effect = AssertionError("STS should not be called")

    container_service, _, _, _ = make_live_tail_service(logs_client=mock_logs_client, sts_client=mock_sts_client)

    list(container_service.get_live_container_logs_tail("/ecs/app", "stream", aws_account_id="999999999999"))

    mock_sts_client.get_caller_identity.assert_not_called()
    mock_logs_client.start_live_tail.assert_called_once_with(
        logGroupIdentifiers=["arn:aws:logs:us-east-1:999999999999:log-group:/ecs/app"],
        logStreamNames=["stream"],
        logEventFilterPattern="",
    )


def test_get_live_container_logs_tail_uses_environment_account_id_when_not_provided(
    make_live_tail_service, monkeypatch
):
    mock_response_stream = Mock()
    mock_response_stream.__iter__ = Mock(return_value=iter([]))

    mock_logs_client = Mock()
    mock_logs_client.start_live_tail.return_value = {"responseStream": mock_response_stream}

    container_service, _, _, _ = make_live_tail_service(logs_client=mock_logs_client, use_sts=False)
    monkeypatch.setenv("AWS_ACCOUNT_ID", "222222222222")

    list(container_service.get_live_container_logs_tail("/ecs/app", "stream"))

    mock_logs_client.start_live_tail.assert_called_once_with(
        logGroupIdentifiers=["arn:aws:logs:us-east-1:222222222222:log-group:/ecs/app"],
        logStreamNames=["stream"],
        logEventFilterPattern="",
    )


def test_list_log_groups_returns_empty_when_no_client(mock_task_service):
    container_service = ContainerService(Mock(), mock_task_service, logs_client=None)

    result = container_service.list_log_groups("production", "web")

    assert result == []


def test_list_log_groups_filters_by_cluster_and_container():
    mock_logs_client = Mock()
    mock_logs_client.describe_log_groups.return_value = {
        "logGroups": [
            {"logGroupName": "/ecs/production-web"},
            {"logGroupName": "/ecs/staging-api"},
            {"logGroupName": "/aws/lambda/function"},
            {"logGroupName": "/ecs/production-worker"},
        ]
    }
    container_service = ContainerService(Mock(), Mock(), logs_client=mock_logs_client)

    result = container_service.list_log_groups("production", "web")

    assert "/ecs/production-web" in result
    assert "/ecs/staging-api" in result  # Contains "ecs" so it's included


def test_list_log_groups_paginates_and_ranks_relevant_matches_first():
    mock_logs_client = Mock()
    mock_logs_client.describe_log_groups.side_effect = [
        {
            "logGroups": [
                {"logGroupName": "/ecs/staging-api"},
                {"logGroupName": "/aws/lambda/function"},
            ],
            "nextToken": "page-2",
        },
        {
            "logGroups": [
                {"logGroupName": "/ecs/production-worker"},
                {"logGroupName": "/ecs/production-web"},
            ]
        },
    ]
    container_service = ContainerService(Mock(), Mock(), logs_client=mock_logs_client)

    result = container_service.list_log_groups("production", "web")

    assert result[0] == "/ecs/production-web"
    assert "/ecs/production-worker" in result
    assert "/ecs/staging-api" in result
    assert "/aws/lambda/function" not in result
    assert mock_logs_client.describe_log_groups.call_args_list == [
        call(limit=50),
        call(limit=50, nextToken="page-2"),
    ]


def test_list_log_groups_uses_service_and_task_family_signals_for_ranking():
    mock_logs_client = Mock()
    mock_logs_client.describe_log_groups.return_value = {
        "logGroups": [
            {"logGroupName": "/ecs/production-web"},
            {"logGroupName": "/ecs/production-api"},
            {"logGroupName": "/ecs/generic"},
            {"logGroupName": "/ecs/payments-worker"},
        ]
    }
    container_service = ContainerService(Mock(), Mock(), logs_client=mock_logs_client)

    result = container_service.list_log_groups(
        "production",
        "worker",
        service_name="api",
        task_family="payments",
    )

    assert result[0] == "/ecs/production-api"
    assert result.index("/ecs/payments-worker") < result.index("/ecs/production-web")


def test_list_log_groups_handles_empty_lookup_values_without_crashing():
    mock_logs_client = Mock()
    mock_logs_client.describe_log_groups.return_value = {
        "logGroups": [
            {"logGroupName": "/ecs/default"},
            {"logGroupName": "/aws/lambda/function"},
        ]
    }
    container_service = ContainerService(Mock(), Mock(), logs_client=mock_logs_client)

    result = container_service.list_log_groups("", "")

    assert result == ["/ecs/default"]


def test_list_log_groups_prioritizes_exact_suffix_match():
    mock_logs_client = Mock()
    mock_logs_client.describe_log_groups.return_value = {
        "logGroups": [
            {"logGroupName": "/ecs/production-web-backup"},
            {"logGroupName": "/ecs/production-web"},
        ]
    }
    container_service = ContainerService(Mock(), Mock(), logs_client=mock_logs_client)

    result = container_service.list_log_groups("production-web", "container")

    assert result[0] == "/ecs/production-web"
