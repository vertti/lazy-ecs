"""Tests for task definition comparison."""

from __future__ import annotations

from lazy_ecs.features.task.comparison import compare_task_definitions, normalize_task_definition


def test_normalize_task_definition_strips_aws_metadata():
    raw_task_def = {
        "taskDefinitionArn": "arn:aws:ecs:us-east-1:123:task-definition/my-app:5",
        "family": "my-app",
        "revision": 5,
        "status": "ACTIVE",
        "registeredAt": "2025-01-01T00:00:00Z",
        "registeredBy": "arn:aws:iam::123:user/john",
        "requiresAttributes": [{"name": "some-attr"}],
        "compatibilities": ["FARGATE"],
        "containerDefinitions": [
            {
                "name": "web",
                "image": "nginx:1.21",
                "cpu": 256,
                "memory": 512,
            },
        ],
    }

    normalized = normalize_task_definition(raw_task_def)

    assert "taskDefinitionArn" not in normalized
    assert "status" not in normalized
    assert "registeredAt" not in normalized
    assert "registeredBy" not in normalized
    assert "requiresAttributes" not in normalized
    assert "compatibilities" not in normalized

    assert normalized["family"] == "my-app"
    assert normalized["revision"] == 5
    assert len(normalized["containers"]) == 1


def test_normalize_task_definition_extracts_container_fields():
    raw_task_def = {
        "family": "my-app",
        "revision": 1,
        "containerDefinitions": [
            {
                "name": "web",
                "image": "nginx:1.21",
                "cpu": 256,
                "memory": 512,
                "environment": [
                    {"name": "ENV", "value": "production"},
                    {"name": "DEBUG", "value": "false"},
                ],
                "secrets": [{"name": "API_KEY", "valueFrom": "arn:aws:secretsmanager:..."}],
                "portMappings": [{"containerPort": 80, "protocol": "tcp"}],
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {"awslogs-group": "/ecs/my-app"},
                },
                "command": ["npm", "start"],
                "entryPoint": ["/bin/sh"],
            },
        ],
    }

    normalized = normalize_task_definition(raw_task_def)

    container = normalized["containers"][0]
    assert container["name"] == "web"
    assert container["image"] == "nginx:1.21"
    assert container["cpu"] == 256
    assert container["memory"] == 512
    assert container["environment"] == {"ENV": "production", "DEBUG": "false"}
    assert container["secrets"] == {"API_KEY": "arn:aws:secretsmanager:..."}
    assert container["ports"] == [{"containerPort": 80, "protocol": "tcp"}]
    assert container["logDriver"] == "awslogs"
    assert container["command"] == ["npm", "start"]
    assert container["entryPoint"] == ["/bin/sh"]


def test_normalize_task_definition_handles_missing_fields():
    raw_task_def = {
        "family": "my-app",
        "revision": 1,
        "containerDefinitions": [
            {
                "name": "web",
                "image": "nginx:1.21",
            },
        ],
    }

    normalized = normalize_task_definition(raw_task_def)

    container = normalized["containers"][0]
    assert container["environment"] == {}
    assert container["secrets"] == {}
    assert container["ports"] == []
    assert container.get("cpu") is None
    assert container.get("memory") is None
    assert container.get("command") is None
    assert container.get("entryPoint") is None


def test_normalize_task_definition_includes_task_level_resources():
    raw_task_def = {
        "family": "my-app",
        "revision": 1,
        "cpu": "512",
        "memory": "1024",
        "containerDefinitions": [{"name": "web", "image": "nginx:1.21"}],
    }

    normalized = normalize_task_definition(raw_task_def)

    assert normalized["taskCpu"] == "512"
    assert normalized["taskMemory"] == "1024"


def test_compare_task_definitions_detects_image_change():
    source = {
        "family": "my-app",
        "revision": 1,
        "containers": [{"name": "web", "image": "nginx:1.20"}],
    }
    target = {
        "family": "my-app",
        "revision": 2,
        "containers": [{"name": "web", "image": "nginx:1.21"}],
    }

    changes = compare_task_definitions(source, target)

    assert len(changes) == 1
    assert changes[0]["type"] == "image_changed"
    assert changes[0]["container"] == "web"
    assert changes[0]["old"] == "nginx:1.20"
    assert changes[0]["new"] == "nginx:1.21"


def test_compare_task_definitions_detects_env_var_changes():
    source = {
        "family": "my-app",
        "revision": 1,
        "containers": [
            {
                "name": "web",
                "image": "nginx:1.21",
                "environment": {"ENV": "staging", "DEBUG": "false"},
            },
        ],
    }
    target = {
        "family": "my-app",
        "revision": 2,
        "containers": [
            {
                "name": "web",
                "image": "nginx:1.21",
                "environment": {"ENV": "production", "LOG_LEVEL": "info"},
            },
        ],
    }

    changes = compare_task_definitions(source, target)

    change_types = {c["type"] for c in changes}
    assert "env_changed" in change_types
    assert "env_added" in change_types
    assert "env_removed" in change_types

    env_changed = next(c for c in changes if c["type"] == "env_changed")
    assert env_changed["key"] == "ENV"
    assert env_changed["old"] == "staging"
    assert env_changed["new"] == "production"

    env_added = next(c for c in changes if c["type"] == "env_added")
    assert env_added["key"] == "LOG_LEVEL"
    assert env_added["value"] == "info"

    env_removed = next(c for c in changes if c["type"] == "env_removed")
    assert env_removed["key"] == "DEBUG"
    assert env_removed["value"] == "false"


def test_compare_task_definitions_detects_resource_changes():
    source = {
        "family": "my-app",
        "revision": 1,
        "taskCpu": "256",
        "taskMemory": "512",
        "containers": [{"name": "web", "image": "nginx:1.21", "cpu": 128, "memory": 256}],
    }
    target = {
        "family": "my-app",
        "revision": 2,
        "taskCpu": "512",
        "taskMemory": "1024",
        "containers": [{"name": "web", "image": "nginx:1.21", "cpu": 256, "memory": 512}],
    }

    changes = compare_task_definitions(source, target)

    change_types = {c["type"] for c in changes}
    assert "task_cpu_changed" in change_types
    assert "task_memory_changed" in change_types
    assert "container_cpu_changed" in change_types
    assert "container_memory_changed" in change_types


def test_compare_task_definitions_detects_secret_changes():
    source = {
        "family": "my-app",
        "revision": 1,
        "containers": [
            {
                "name": "web",
                "image": "nginx:1.21",
                "secrets": {"API_KEY": "arn:aws:secretsmanager:us-east-1:123:secret:api-key-v1"},
            },
        ],
    }
    target = {
        "family": "my-app",
        "revision": 2,
        "containers": [
            {
                "name": "web",
                "image": "nginx:1.21",
                "secrets": {"API_KEY": "arn:aws:secretsmanager:us-east-1:123:secret:api-key-v2"},
            },
        ],
    }

    changes = compare_task_definitions(source, target)

    assert len(changes) == 1
    assert changes[0]["type"] == "secret_changed"
    assert changes[0]["key"] == "API_KEY"


def test_compare_task_definitions_no_changes():
    source = {
        "family": "my-app",
        "revision": 1,
        "containers": [{"name": "web", "image": "nginx:1.21"}],
    }
    target = {
        "family": "my-app",
        "revision": 2,
        "containers": [{"name": "web", "image": "nginx:1.21"}],
    }

    changes = compare_task_definitions(source, target)

    assert len(changes) == 0


def test_compare_task_definitions_detects_port_changes():
    source = {
        "family": "my-app",
        "revision": 1,
        "containers": [
            {
                "name": "web",
                "image": "nginx:1.21",
                "ports": [{"containerPort": 80, "protocol": "tcp"}],
            },
        ],
    }
    target = {
        "family": "my-app",
        "revision": 2,
        "containers": [
            {
                "name": "web",
                "image": "nginx:1.21",
                "ports": [{"containerPort": 8080, "protocol": "tcp"}],
            },
        ],
    }

    changes = compare_task_definitions(source, target)

    assert len(changes) == 1
    assert changes[0]["type"] == "ports_changed"
    assert changes[0]["container"] == "web"


def test_compare_task_definitions_detects_command_changes():
    source = {
        "family": "my-app",
        "revision": 1,
        "containers": [{"name": "web", "image": "nginx:1.21", "command": ["npm", "start"]}],
    }
    target = {
        "family": "my-app",
        "revision": 2,
        "containers": [{"name": "web", "image": "nginx:1.21", "command": ["npm", "run", "prod"]}],
    }

    changes = compare_task_definitions(source, target)

    assert len(changes) == 1
    assert changes[0]["type"] == "command_changed"
    assert changes[0]["container"] == "web"
    assert changes[0]["old"] == ["npm", "start"]
    assert changes[0]["new"] == ["npm", "run", "prod"]


def test_compare_task_definitions_detects_entrypoint_changes():
    source = {
        "family": "my-app",
        "revision": 1,
        "containers": [{"name": "web", "image": "nginx:1.21", "entryPoint": ["/bin/sh"]}],
    }
    target = {
        "family": "my-app",
        "revision": 2,
        "containers": [{"name": "web", "image": "nginx:1.21", "entryPoint": ["/bin/bash"]}],
    }

    changes = compare_task_definitions(source, target)

    assert len(changes) == 1
    assert changes[0]["type"] == "entrypoint_changed"
    assert changes[0]["container"] == "web"
    assert changes[0]["old"] == ["/bin/sh"]
    assert changes[0]["new"] == ["/bin/bash"]


def test_compare_task_definitions_detects_volume_changes():
    source = {
        "family": "my-app",
        "revision": 1,
        "containers": [
            {
                "name": "web",
                "image": "nginx:1.21",
                "mountPoints": [{"sourceVolume": "data", "containerPath": "/data"}],
            },
        ],
    }
    target = {
        "family": "my-app",
        "revision": 2,
        "containers": [
            {
                "name": "web",
                "image": "nginx:1.21",
                "mountPoints": [{"sourceVolume": "data", "containerPath": "/var/data"}],
            },
        ],
    }

    changes = compare_task_definitions(source, target)

    assert len(changes) == 1
    assert changes[0]["type"] == "volumes_changed"
    assert changes[0]["container"] == "web"
