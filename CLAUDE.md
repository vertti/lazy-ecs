# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`lazy-ecs` is a CLI tool for working with AWS services, with initial focus on Amazon ECS. Built with modern Python tooling including uv for dependency management, ruff for linting/formatting, and pytest for testing.

## Development Environment

The project uses:
- `uv` for Python dependency management and virtual environments
- `mise` for tool management (Python, uv, Node.js)
- Python 3.11+ required

## Development Workflow (Test-Driven Development)

**This project follows a strict TDD approach:**

1. **Write a test** for the new feature/functionality
2. **Run the test** to see it fail: `uv run pytest`
3. **Implement** the minimal code to make the test pass
4. **Run tests** again to verify they pass: `uv run pytest`
5. **Format code**: `uv run ruff format` (fixes many linting issues automatically)
6. **Check linting**: `uv run ruff check`
7. **Pause** - suggest commit message, never commit automatically

## Common Commands

```bash
# Install dependencies and dev dependencies
uv sync

# Run the CLI
uv run lazy-ecs

# TDD Cycle Commands (in order):
uv run pytest                    # Run tests (should fail initially)
# [implement feature]
uv run pytest                    # Verify tests pass
uv run ruff format               # Auto-fix formatting (run first!)
uv run ruff check                # Check remaining linting issues

# Other useful commands:
uv run pytest --cov             # Run tests with coverage
uv run pytest -v                # Verbose test output
uv run pytest tests/test_file.py # Run specific test file
```

**IMPORTANT**: This is a uv project - always prefix commands with `uv run` or `uv`.

## Project Structure

- `src/lazy_ecs/` - Main application code using Click for CLI
- `tests/` - Test files using pytest
- `pyproject.toml` - All configuration (dependencies, tools, build)

## Architecture

- **CLI Framework**: Click for command-line interface with rich output
- **AWS Integration**: boto3 for AWS API interactions
- **Project Layout**: src-layout with lazy_ecs package
- **Testing**: pytest with coverage reporting
- **Code Quality**: ruff for linting and formatting
- **Entry Point**: `lazy-ecs` command installed as script

## Key Features

- Modern Python packaging with pyproject.toml
- Rich console output for better UX
- Structured CLI with subcommands (e.g., `lazy-ecs ecs list-clusters`)
- Comprehensive test coverage setup
- All tooling configured in pyproject.toml