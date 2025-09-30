"""Tests for cluster UI components."""

from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

from lazy_ecs.features.cluster.cluster import ClusterService
from lazy_ecs.features.cluster.ui import ClusterUI


@pytest.fixture
def cluster_service_with_many_clusters():
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")

        for i in range(100):
            client.create_cluster(clusterName=f"cluster-{i:03d}")

        yield ClusterService(client)


@patch("lazy_ecs.features.cluster.ui.select_with_auto_pagination")
def test_select_cluster_with_pagination(mock_select, cluster_service_with_many_clusters):
    mock_select.return_value = "cluster-050"

    cluster_ui = ClusterUI(cluster_service_with_many_clusters)
    result = cluster_ui.select_cluster()

    assert result == "cluster-050"
    mock_select.assert_called_once()

    call_args = mock_select.call_args
    choices = call_args[0][1]
    assert len(choices) == 100


@patch("lazy_ecs.features.cluster.ui.select_with_auto_pagination")
def test_select_cluster_without_pagination_small_list(mock_select):
    with mock_aws():
        client = boto3.client("ecs", region_name="us-east-1")
        for i in range(5):
            client.create_cluster(clusterName=f"cluster-{i}")

        cluster_service = ClusterService(client)
        mock_select.return_value = "cluster-2"

        cluster_ui = ClusterUI(cluster_service)
        result = cluster_ui.select_cluster()

        assert result == "cluster-2"
        mock_select.assert_called_once()


@patch("lazy_ecs.features.cluster.ui.select_with_auto_pagination")
def test_select_cluster_navigation_exit(mock_select, cluster_service_with_many_clusters):
    mock_select.return_value = "navigation:exit"

    cluster_ui = ClusterUI(cluster_service_with_many_clusters)
    result = cluster_ui.select_cluster()

    assert result == ""
