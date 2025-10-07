"""Tests for task UI formatting functions."""

import pytest

from lazy_ecs.features.task.ui import _format_ports, _format_volumes


@pytest.mark.parametrize(
    ("ports", "expected"),
    [
        ([], "none"),
        ([{"containerPort": 8080, "protocol": "tcp"}], "8080/tcp"),
        ([{"containerPort": 8080, "hostPort": 80, "protocol": "tcp"}], "80:8080/tcp"),
        (
            [
                {"containerPort": 8080, "hostPort": 80, "protocol": "tcp"},
                {"containerPort": 443, "protocol": "tcp"},
                {"containerPort": 53, "protocol": "udp"},
            ],
            "80:8080/tcp, 443/tcp, 53/udp",
        ),
        ([{"containerPort": 3000}], "3000/tcp"),
    ],
)
def test_format_ports(ports, expected):
    assert _format_ports(ports) == expected


@pytest.mark.parametrize(
    ("volumes", "expected"),
    [
        ([], "none"),
        ([{"sourceVolume": "data", "containerPath": "/app/data"}], "data:/app/data"),
        ([{"sourceVolume": "config", "containerPath": "/etc/config", "readOnly": True}], "config:/etc/config:ro"),
        (
            [
                {"sourceVolume": "data", "containerPath": "/app/data"},
                {"sourceVolume": "logs", "containerPath": "/var/log", "readOnly": True},
                {"sourceVolume": "cache", "containerPath": "/app/cache"},
            ],
            "data:/app/data, logs:/var/log:ro, cache:/app/cache",
        ),
    ],
)
def test_format_volumes(volumes, expected):
    assert _format_volumes(volumes) == expected


def test_format_volumes_missing_fields():
    assert "data:?" in _format_volumes([{"sourceVolume": "data"}])
