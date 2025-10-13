#!/bin/bash
set -e

# Build script for all MCP server Docker images
# Usage: ./build-all.sh [registry]

REGISTRY="${1:-mcp-servers}"
VERSION="${2:-latest}"

echo "Building MCP server images..."
echo "Registry: $REGISTRY"
echo "Version: $VERSION"

# Navigate to project root
cd "$(dirname "$0")/../.."

# Build base image first
echo "Building base image..."
docker build \
  -f cloud/docker/Dockerfile.base \
  -t ${REGISTRY}/base:${VERSION} \
  .

# Build all server images
SERVERS=("memory-cache" "goal-agent" "github" "jira" "internet")

for server in "${SERVERS[@]}"; do
  echo "Building ${server} image..."
  docker build \
    -f cloud/docker/Dockerfile.${server} \
    -t ${REGISTRY}/${server}:${VERSION} \
    .
done

echo "All images built successfully!"
echo ""
echo "To push to registry:"
for server in "${SERVERS[@]}"; do
  echo "  docker push ${REGISTRY}/${server}:${VERSION}"
done

