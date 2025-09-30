"""Shared pytest fixtures for tests."""

from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_paginated_client():
    """Create a mock AWS client with paginator support.

    Returns a factory function that creates clients with specified pagination pages.

    Example:
        def test_something(mock_paginated_client):
            pages = [{"clusterArns": ["arn1", "arn2"]}]
            client = mock_paginated_client(pages)
    """

    def _create_client(pages: list[dict]) -> Mock:
        client = Mock()
        paginator = Mock()
        paginator.paginate.return_value = pages
        client.get_paginator.return_value = paginator
        return client

    return _create_client
