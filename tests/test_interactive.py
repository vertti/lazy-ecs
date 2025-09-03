from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

from lazy_ecs.interactive import ECSNavigator


@pytest.fixture
def ecs_client_with_clusters():
    """Create a mocked ECS client with test clusters."""
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")

        # Create test clusters
        client.create_cluster(clusterName="production")
        client.create_cluster(clusterName="staging")
        client.create_cluster(clusterName="dev")

        yield client


@pytest.fixture
def ecs_client_empty():
    """Create a mocked ECS client with no clusters."""
    with mock_aws():
        yield boto3.client("ecs", region_name="us-east-1")


def test_get_cluster_names(ecs_client_with_clusters):
    navigator = ECSNavigator(ecs_client_with_clusters)
    clusters = navigator.get_cluster_names()

    expected = ["production", "staging", "dev"]
    assert sorted(clusters) == sorted(expected)


@patch("lazy_ecs.interactive.questionary.select")
def test_select_cluster_interactive(mock_select, ecs_client_with_clusters):
    mock_select.return_value.ask.return_value = "production"

    navigator = ECSNavigator(ecs_client_with_clusters)
    selected = navigator.select_cluster()

    assert selected == "production"
    mock_select.assert_called_once()


def test_cluster_selection_with_no_clusters(ecs_client_empty):
    navigator = ECSNavigator(ecs_client_empty)
    clusters = navigator.get_cluster_names()

    assert clusters == []


@patch("lazy_ecs.interactive.questionary.select")
def test_select_cluster_interactive_no_clusters(mock_select, ecs_client_empty):
    """Test interactive selection when no clusters exist."""
    navigator = ECSNavigator(ecs_client_empty)
    selected = navigator.select_cluster()

    # Should return empty string when no clusters
    assert selected == ""
    # questionary.select should not be called when no clusters
    mock_select.assert_not_called()
