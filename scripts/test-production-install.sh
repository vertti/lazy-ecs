#!/usr/bin/env bash
set -euo pipefail

echo "🧪 Testing production install (simple version)..."

# Save current directory (should be project root)
PROJECT_ROOT="$(pwd)"

# Generate production requirements from pyproject.toml (exclude our own package)
echo "Generating production requirements..."
uv export --format requirements-txt --no-dev --no-emit-project > /tmp/requirements.txt

# Create temp dir and venv
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"
python3 -m venv test_env
source test_env/bin/activate

# Install production dependencies
echo "Installing production dependencies from pyproject.toml..."
pip install --quiet -r /tmp/requirements.txt

# Clean old builds and build fresh
echo "Installing lazy-ecs..."
cd "$PROJECT_ROOT"
rm -rf dist/
uv build --quiet
pip install --quiet --no-deps dist/lazy_ecs-*.tar.gz

# Test
echo "Testing..."
python3 -c "
from lazy_ecs.aws_service import ECSService
from lazy_ecs.ui import ECSNavigator  
from lazy_ecs import main
print('✅ Production install test passed!')
"

# Cleanup
deactivate
rm -rf "$TEMP_DIR"