# lazy-ecs

A CLI tool for navigating AWS ECS clusters interactively.

![lazy-ecs demo](images/lazy-ecs-demo.jpg)

## Why I Built This

When running services in ECS, I constantly needed to check:

- What exactly is running where?
- Is my service healthy?
- What parameters or environment variables got applied?
- What do the latest logs show - did the container start as expected?

The AWS ECS web console is confusing to navigate, with multiple clicks through different screens just to get basic information. The AWS CLI is powerful but verbose and requires memorizing complex commands.

**lazy-ecs** solves this with a simple, interactive CLI that lets you quickly drill down from clusters → services → tasks → containers with just arrow keys. It destroys the AWS CLI in usability for ECS exploration and debugging.

## Installation

### Homebrew (Recommended)

```bash
# Add the tap
brew tap vertti/lazy-ecs

# Install lazy-ecs
brew install lazy-ecs

# Run it
lazy-ecs
```

### From Source

```bash
# Clone and install with uv
git clone https://github.com/vertti/lazy-ecs.git
cd lazy-ecs
uv sync
uv run lazy-ecs
```

## AWS Authentication

lazy-ecs supports multiple ways to authenticate with AWS:

### 1. AWS Profile (--profile flag)

```bash
lazy-ecs --profile your-profile-name
```

### 2. Environment Variables

```bash
export AWS_DEFAULT_PROFILE=your-profile-name
lazy-ecs
```

### 3. AWS Vault

```bash
aws-vault exec Platform-Test.AWSAdministratorAccess -- lazy-ecs
```

### 4. Default Credentials Chain

lazy-ecs will automatically use the standard AWS credentials chain:

- Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
- AWS credentials file (~/.aws/credentials)
- IAM instance profile (when running on EC2)

## Features

### Container-Level Features 🚀

- ✅ **Container log viewing** - Display recent logs with timestamps from CloudWatch
- ✅ **Container log live tail viewing** - Display logs live tail with timestamps from CloudWatch
- ✅ **Basic container details** - Show container name, image, CPU/memory configuration
- ✅ **Show environment variables & secrets** - Display environment variables and secrets configuration (without exposing secret values)
- ✅ **Show port mappings** - Display container port configurations and networking
- ✅ **Show volume mounts** - Display file system mounts and storage configuration
- ⬜ **Show resource limits vs usage** - Display CPU/memory limits and actual consumption
- ⬜ **Show health check configuration** - Display health check settings and current status
- ⬜ **Connect to running container** - Execute shell commands inside running containers (skip - against immutable philosophy)
- ⬜ **Export container environment** - Save environment variables to .env file for local development
- ⬜ **Copy container command** - Get exact docker run command for local debugging

### Task-Level Features 📋

- ✅ **Task selection with auto-selection** - Automatically select single tasks, interactive selection for multiple
- ✅ **Comprehensive task details** - Display task definition, status, containers, creation time
- ✅ **Task definition version tracking** - Show if task is running desired vs outdated version
- ✅ **Show task events/history** - Display task lifecycle events and failure reasons with smart analysis (OOM kills, timeouts, image pull failures)
- ⬜ **Show task placement details** - Display placement constraints and actual host placement
- ⬜ **Task definition comparison** - Compare current vs desired task definition versions
- ⬜ **Show security groups** - Display networking and security configuration
- ⬜ **Export task definition** - Save task definition as JSON/YAML files
- ⬜ **Stop/Restart single task** - Manually stop tasks for debugging (service will auto-restart)
- ⬜ **Quick task failure reason** - Show failure reason inline without navigation

### Service-Level Features 🔧

- ✅ **Service browsing with status** - Display services with health indicators (healthy/scaling/over-scaled)
- ✅ **Service status indicators** - Show running/desired/pending counts with visual status
- ✅ **Force new deployment** - Trigger service redeployment directly from CLI (no more AWS console trips!)
- ✅ **Show service events** - Display service-level events and deployment status with chronological sorting and proper categorization
- ⬜ **Show deployment history** - Display service deployment timeline and rollback options
- ⬜ **Show auto-scaling configuration** - Display scaling policies and current metrics
- ⬜ **Show load balancer health** - Display target group health and routing configuration
- ⬜ **Service update (image tag)** - Update service with new image tag
- ⬜ **Service update (environment)** - Update environment variables for service

### Cluster-Level Features 🏗️

- ✅ **Interactive cluster selection** - Arrow key navigation through available ECS clusters
- ✅ **Log group discovery** - Automatically find relevant log groups for debugging
- ⬜ **Multi-cluster support** - Compare resources across clusters
- ⬜ **Bulk operations across clusters** - Perform operations on multiple clusters

### Advanced Features 🎯

- ⬜ **Enhanced log features**:
  - ⬜ Search/filter logs by keywords or time range
  - ✅ Follow logs in real-time (tail -f style) - complex UI implementation
  - ⬜ Download logs to file
- ⬜ **Monitoring integration**:
  - ⬜ Show CloudWatch metrics for containers/tasks
  - ⬜ Display resource utilization trends
- ⬜ **Port forwarding to container** - Direct local connection to container ports for debugging
- ⬜ **Multi-region support** - Work with ECS across different AWS regions

## Development

### Prerequisites

Install tools with [mise](https://mise.jdx.dev/):

```bash
mise install
```

### Setup

Setup and development commands can also be ran with [GNU Make](https://www.gnu.org/software/make/). You can also view available commands with Make using `make`.

```
Available commands:
  install         --> Install dependencies
  precminit       --> Install pre-commit hooks (runs ruff formatting/linting on commit)
  run             --> Run 'lazy-ecs' CLI (use 'make run PROFILE=<profile-name>' to specify your desired AWS profile)
  test            --> Run tests using 'pytest'
  format          --> Format and lint code (with type annotation enforcement)
  formatfix       --> Format, lint, and fix code (with type annotation enforcement)
  pyrefly         --> Type checking with 'pyrefly'
  reflyinf        --> Auto-add missing type annotations with 'pyrefly'
  testcov         --> Run tests with coverage

Targets that accept arguments:
  test ARGS="..." --> Example: make test ARGS=tests/test_file.py
```

Using `uv`

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
