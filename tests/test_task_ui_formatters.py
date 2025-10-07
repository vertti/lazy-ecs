"""Tests for task UI formatting functions."""

from lazy_ecs.features.task.ui import _format_ports, _format_volumes


def test_format_ports_empty_list():
    result = _format_ports([])

    assert result == "none"


def test_format_ports_single_port_without_host():
    ports = [{"containerPort": 8080, "protocol": "tcp"}]

    result = _format_ports(ports)

    assert result == "8080/tcp"


def test_format_ports_single_port_with_host():
    ports = [{"containerPort": 8080, "hostPort": 80, "protocol": "tcp"}]

    result = _format_ports(ports)

    assert result == "80:8080/tcp"


def test_format_ports_multiple_ports():
    ports = [
        {"containerPort": 8080, "hostPort": 80, "protocol": "tcp"},
        {"containerPort": 443, "protocol": "tcp"},
        {"containerPort": 53, "protocol": "udp"},
    ]

    result = _format_ports(ports)

    assert result == "80:8080/tcp, 443/tcp, 53/udp"


def test_format_ports_missing_protocol_defaults_to_tcp():
    ports = [{"containerPort": 3000}]

    result = _format_ports(ports)

    assert result == "3000/tcp"


def test_format_volumes_empty_list():
    result = _format_volumes([])

    assert result == "none"


def test_format_volumes_single_volume_read_write():
    volumes = [{"sourceVolume": "data", "containerPath": "/app/data"}]

    result = _format_volumes(volumes)

    assert result == "data:/app/data"


def test_format_volumes_single_volume_read_only():
    volumes = [{"sourceVolume": "config", "containerPath": "/etc/config", "readOnly": True}]

    result = _format_volumes(volumes)

    assert result == "config:/etc/config:ro"


def test_format_volumes_multiple_volumes():
    volumes = [
        {"sourceVolume": "data", "containerPath": "/app/data"},
        {"sourceVolume": "logs", "containerPath": "/var/log", "readOnly": True},
        {"sourceVolume": "cache", "containerPath": "/app/cache"},
    ]

    result = _format_volumes(volumes)

    assert result == "data:/app/data, logs:/var/log:ro, cache:/app/cache"


def test_format_volumes_missing_fields_shows_question_mark():
    volumes = [{"sourceVolume": "data"}]

    result = _format_volumes(volumes)

    assert "data:?" in result
