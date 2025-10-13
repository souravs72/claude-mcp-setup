#!/bin/bash
set -e

# Docker-based Cloud Deployment
# Run deployment from a container - no local tools needed!

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "========================================"
echo "Docker-Based Cloud Deployment"
echo "========================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✓ Docker is running"
echo ""

# Build deployer image if it doesn't exist
if ! docker images | grep -q "mcp-deployer"; then
    echo "Building deployer container..."
    docker build -t mcp-deployer -f "$SCRIPT_DIR/Dockerfile.deployer" "$SCRIPT_DIR"
    echo "✓ Deployer container built"
else
    echo "✓ Deployer container already exists"
fi

echo ""
echo "Launching deployment container..."
echo ""

# Run deployment in container
docker run -it --rm \
    -v "$PROJECT_ROOT:/workspace" \
    -v "$HOME/.aws:/root/.aws:ro" \
    -v "$HOME/.kube:/root/.kube" \
    -v "/var/run/docker.sock:/var/run/docker.sock" \
    -e AWS_REGION=ap-south-1 \
    --workdir /workspace/cloud \
    mcp-deployer \
    bash -c "
        echo '========================================'
        echo 'MCP Cloud Deployment Container'
        echo '========================================'
        echo ''
        echo 'Available commands:'
        echo '  ./deploy.sh production aws'
        echo '  terraform init && terraform apply'
        echo '  helm install mcp-servers ./helm/mcp-servers'
        echo '  kubectl get pods -n mcp-servers'
        echo ''
        echo 'Or run: ./deploy.sh production aws'
        echo ''
        exec bash
    "

