# lazy-ecs

A CLI tool for navigating AWS ECS clusters interactively.

## Why?

The AWS console UI is confusing to navigate for ECS. This tool makes it quick to check exactly what is running in your ECS clusters, drill down to specific services and tasks, all with simple arrow key navigation.

## Features

### Container-Level Features 🚀

- [x] **Container log viewing** - Display recent logs with timestamps from CloudWatch
- [x] **Basic container details** - Show container name, image, CPU/memory configuration
- [x] **Show environment variables** - Display all environment variables injected into containers
- [ ] **Show port mappings** - Display container port configurations and networking
- [ ] **Show volume mounts** - Display file system mounts and storage configuration  
- [ ] **Show resource limits vs usage** - Display CPU/memory limits and actual consumption
- [ ] **Show health check configuration** - Display health check settings and current status
- [ ] **Connect to running container** - Execute shell commands inside running containers

### Task-Level Features 📋

- [x] **Task selection with auto-selection** - Automatically select single tasks, interactive selection for multiple
- [x] **Comprehensive task details** - Display task definition, status, containers, creation time
- [x] **Task definition version tracking** - Show if task is running desired vs outdated version
- [ ] **Show task placement details** - Display placement constraints and actual host placement
- [ ] **Task definition comparison** - Compare current vs desired task definition versions
- [ ] **Show task events/history** - Display task lifecycle events and failure reasons
- [ ] **Show security groups** - Display networking and security configuration
- [ ] **Export task definition** - Save task definition as JSON/YAML files

### Service-Level Features 🔧

- [x] **Service browsing with status** - Display services with health indicators (healthy/scaling/over-scaled)
- [x] **Service status indicators** - Show running/desired/pending counts with visual status
- [ ] **Show deployment history** - Display service deployment timeline and rollback options
- [ ] **Show auto-scaling configuration** - Display scaling policies and current metrics
- [ ] **Show load balancer health** - Display target group health and routing configuration
- [ ] **Show service events** - Display service-level events and deployment status

### Cluster-Level Features 🏗️

- [x] **Interactive cluster selection** - Arrow key navigation through available ECS clusters
- [x] **Log group discovery** - Automatically find relevant log groups for debugging
- [ ] **Multi-cluster support** - Compare resources across clusters
- [ ] **Bulk operations across clusters** - Perform operations on multiple clusters

### Advanced Features 🎯

- [ ] **Enhanced log features**:
  - [ ] Search/filter logs by keywords or time range
  - [ ] Follow logs in real-time (tail -f style) 
  - [ ] Download logs to file
- [ ] **Monitoring integration**:
  - [ ] Show CloudWatch metrics for containers/tasks
  - [ ] Display resource utilization trends

## Development

### Prerequisites

Install tools with [mise](https://mise.jdx.dev/):

```bash
mise install
```

### Setup

```bash
# Install dependencies
uv sync

# Install pre-commit hooks (runs ruff formatting/linting on commit)
uv run pre-commit install
```

### Development Commands

```bash
# Run the CLI
uv run lazy-ecs

# Run tests
uv run pytest

# Format and lint code (with type annotation enforcement)
uv run ruff format
uv run ruff check --fix

# Type checking with pyrefly
uv run pyrefly check

# Auto-add missing type annotations
uv run pyrefly infer

# Run tests with coverage
uv run pytest --cov
```

See [CLAUDE.md](CLAUDE.md) for detailed development guidelines.