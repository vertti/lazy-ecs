#!/usr/bin/env bash
set -euo pipefail

# Generate Homebrew resource blocks using homebrew-pypi-poet
# Usage: generate-homebrew-resources.sh

# Create temporary directory
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

echo "Setting up temporary environment..." >&2

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the package and poet
echo "Installing lazy-ecs and homebrew-pypi-poet..." >&2
pip install lazy-ecs homebrew-pypi-poet

# Generate resource stanzas
echo "Generating resource blocks..." >&2
poet lazy-ecs

# Clean up
deactivate
rm -rf "$TEMP_DIR"