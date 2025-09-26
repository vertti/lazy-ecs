help:
	@printf "Available commands:\n"
	@printf "  %-15s --> %s\n" "install" "Install dependencies"
	@printf "  %-15s --> %s\n" "precminit" "Install pre-commit hooks (runs ruff formatting/linting on commit)"
	@printf "  %-15s --> %s\n" "run" "Run 'lazy-ecs' CLI (use 'make run PROFILE=<profile-name>' to specify your desired AWS profile)"
	@printf "  %-15s --> %s\n" "test" "Run tests using 'pytest'"
	@printf "  %-15s --> %s\n" "format" "Format and lint code (with type annotation enforcement)"
	@printf "  %-15s --> %s\n" "formatfix" "Format, lint, and fix code (with type annotation enforcement)"
	@printf "  %-15s --> %s\n" "pyrefly" "Type checking with 'pyrefly'"
	@printf "  %-15s --> %s\n" "reflyinf" "Auto-add missing type annotations with 'pyrefly'"
	@printf "  %-15s --> %s\n" "testcov" "Run tests with coverage"
	@printf "\nTargets that accept arguments:\n"
	@printf "  %-15s --> %s\n" "test ARGS=\"...\"" "Example: make test ARGS=tests/test_file.py"

install:
	@uv sync

precminit:
	@uv run pre-commit install

run:
	@uv run lazy-ecs $(if $(PROFILE),--profile $(PROFILE),)

test:
	@uv run pytest $(ARGS)

format:
	@uv run ruff format

formatfix:
	@uv run ruff check --fix

pyrefly:
	@uv run pyrefly check

reflyinf:
	@uv run pyrefly infer

testcov:
	@uv run pytest --cov
