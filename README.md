# lazy-ecs

A CLI tool for navigating AWS ECS clusters interactively.

## Why?

The AWS console UI is confusing to navigate for ECS. This tool makes it quick to check exactly what is running in your ECS clusters, drill down to specific services and tasks, all with simple arrow key navigation.

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