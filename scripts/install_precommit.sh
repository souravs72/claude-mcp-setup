#!/bin/bash
# Install pre-commit hooks for MCP Servers project

echo "🔧 Installing pre-commit hooks..."

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "📦 Installing pre-commit..."
    pip install pre-commit
fi

# Install the hooks
echo "📋 Installing pre-commit hooks from .pre-commit-config.yaml..."
pre-commit install

# Install pre-push hook for server tests
echo "🚀 Installing pre-push hook for MCP server tests..."
pre-commit install --hook-type pre-push

echo "✅ Pre-commit hooks installed successfully!"
echo ""
echo "📝 Available hooks:"
echo "  - Black code formatting"
echo "  - isort import sorting"
echo "  - Flake8 linting"
echo "  - MyPy type checking"
echo "  - YAML/JSON validation"
echo "  - MCP server tests (pre-push)"
echo ""
echo "🎯 Usage:"
echo "  pre-commit run --all-files    # Run on all files"
echo "  pre-commit run                # Run on staged files"
echo "  git commit                    # Automatically runs on commit"
