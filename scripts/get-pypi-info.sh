#!/usr/bin/env bash
set -euo pipefail

# Get PyPI package information for a given package name and version
# Usage: get-pypi-info.sh <package-name> <version>

PACKAGE_NAME="${1:-}"
VERSION="${2:-}"

if [[ -z "$PACKAGE_NAME" || -z "$VERSION" ]]; then
    echo "Usage: $0 <package-name> <version>" >&2
    exit 1
fi

# Wait for PyPI to process the upload
echo "Waiting for PyPI to process package..." >&2
sleep 30

# Get package info from PyPI API
PYPI_JSON=$(curl -s "https://pypi.org/pypi/$PACKAGE_NAME/$VERSION/json")

# Extract download URL for source distribution
DOWNLOAD_URL=$(echo "$PYPI_JSON" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for url_info in data['urls']:
    if url_info['packagetype'] == 'sdist':
        print(url_info['url'])
        break
else:
    print('ERROR: No source distribution found', file=sys.stderr)
    sys.exit(1)
")

# Extract SHA256 hash
SHA256=$(echo "$PYPI_JSON" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for url_info in data['urls']:
    if url_info['packagetype'] == 'sdist':
        print(url_info['digests']['sha256'])
        break
else:
    print('ERROR: No source distribution found', file=sys.stderr)
    sys.exit(1)
")

# Output for GitHub Actions
echo "PYPI_DOWNLOAD_URL=$DOWNLOAD_URL"
echo "PACKAGE_SHA256=$SHA256"