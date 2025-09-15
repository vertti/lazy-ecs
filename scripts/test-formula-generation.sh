#!/usr/bin/env bash
set -euo pipefail

# Test formula generation locally
echo "Testing formula generation..."

# Set test environment variables
export PYPI_DOWNLOAD_URL="https://files.pythonhosted.org/packages/test/lazy_ecs-0.1.0.tar.gz"
export PACKAGE_SHA256="test-sha256"

# Generate real resources
echo "Generating resources..." >&2
export HOMEBREW_RESOURCES=$(./scripts/generate-homebrew-resources.sh)

# Generate formula
mkdir -p test-output
cat > test-output/lazy-ecs.rb << EOF
class LazyEcs < Formula
  include Language::Python::Virtualenv

  desc "Interactive CLI tool for navigating AWS ECS clusters"
  homepage "https://github.com/vertti/lazy-ecs"
  url "${PYPI_DOWNLOAD_URL}"
  sha256 "${PACKAGE_SHA256}"
  license "MIT"

  depends_on "python@3.11"

${HOMEBREW_RESOURCES}

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "lazy-ecs", shell_output("#{bin}/lazy-ecs --help")
  end
end
EOF

echo "Generated formula:"
cat test-output/lazy-ecs.rb

echo ""
echo "Testing Ruby syntax..."
ruby -c test-output/lazy-ecs.rb

echo "Checking for binary symlink line..."
if grep -q "bin.install_symlink" test-output/lazy-ecs.rb; then
    echo "✅ Binary symlink found"
else
    echo "❌ Missing binary symlink - executable won't be available in PATH"
    exit 1
fi

echo "✅ Formula generation test passed!"
rm -rf test-output