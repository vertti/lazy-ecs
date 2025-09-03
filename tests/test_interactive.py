from unittest.mock import Mock, patch

import pytest

from lazy_ecs.interactive import ECSNavigator


@pytest.fixture
def mock_ecs_client():
    client = Mock()
    client.list_clusters.return_value = {
        "clusterArns": [
            "arn:aws:ecs:us-east-1:123456789012:cluster/production",
            "arn:aws:ecs:us-east-1:123456789012:cluster/staging",
            "arn:aws:ecs:us-east-1:123456789012:cluster/dev",
        ]
    }
    return client


def test_get_cluster_names(mock_ecs_client):
    navigator = ECSNavigator(mock_ecs_client)
    clusters = navigator.get_cluster_names()

    expected = ["production", "staging", "dev"]
    assert clusters == expected
    mock_ecs_client.list_clusters.assert_called_once()


@patch("lazy_ecs.interactive.questionary.select")
def test_select_cluster_interactive(mock_select, mock_ecs_client):
    mock_select.return_value.ask.return_value = "production"

    navigator = ECSNavigator(mock_ecs_client)
    selected = navigator.select_cluster()

    assert selected == "production"
    mock_select.assert_called_once()


def test_cluster_selection_with_no_clusters():
    client = Mock()
    client.list_clusters.return_value = {"clusterArns": []}

    navigator = ECSNavigator(client)
    clusters = navigator.get_cluster_names()

    assert clusters == []
