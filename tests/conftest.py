"""Shared pytest fixtures for tests."""

from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_paginated_client():
    def _create_client(pages: list[dict]) -> Mock:
        client = Mock()
        paginator = Mock()
        paginator.paginate.return_value = pages
        client.get_paginator.return_value = paginator
        return client

    return _create_client


@pytest.fixture
def mock_ecs_client():
    return Mock()
