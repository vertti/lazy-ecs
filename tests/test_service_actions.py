from unittest.mock import Mock

from botocore.exceptions import ClientError, EndpointConnectionError

from lazy_ecs.features.service.actions import ServiceActions


def test_force_new_deployment_success_returns_true_and_no_error():
    mock_ecs_client = Mock()
    mock_ecs_client.update_service.return_value = {"service": {"serviceName": "web-api"}}

    actions = ServiceActions(mock_ecs_client)
    success, error = actions.force_new_deployment("cluster", "web-api")

    assert success is True
    assert error is None


def test_force_new_deployment_access_denied_returns_actionable_error():
    mock_ecs_client = Mock()
    mock_ecs_client.update_service.side_effect = ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "User is not authorized"}},
        "UpdateService",
    )

    actions = ServiceActions(mock_ecs_client)
    success, error = actions.force_new_deployment("cluster", "web-api")

    assert success is False
    assert error == "AccessDeniedException: User is not authorized"


def test_force_new_deployment_service_not_found_returns_actionable_error():
    mock_ecs_client = Mock()
    mock_ecs_client.update_service.side_effect = ClientError(
        {"Error": {"Code": "ServiceNotFoundException", "Message": "Service was not found"}},
        "UpdateService",
    )

    actions = ServiceActions(mock_ecs_client)
    success, error = actions.force_new_deployment("cluster", "web-api")

    assert success is False
    assert error == "ServiceNotFoundException: Service was not found"


def test_force_new_deployment_botocore_error_returns_message():
    mock_ecs_client = Mock()
    mock_ecs_client.update_service.side_effect = EndpointConnectionError(endpoint_url="https://ecs.us-east-1.amazonaws.com")

    actions = ServiceActions(mock_ecs_client)
    success, error = actions.force_new_deployment("cluster", "web-api")

    assert success is False
    assert error is not None
    assert "Could not connect" in error
