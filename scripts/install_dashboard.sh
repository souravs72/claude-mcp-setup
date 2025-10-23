#!/bin/bash
# Quick installer for the MCP Dashboard

set -e

echo "=================================================="
echo "         MCP Dashboard Quick Install"
echo "=================================================="
echo ""

# Check if in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: Not in a virtual environment"
    echo "   Recommended: source mcp-env/bin/activate"
    echo ""
fi

# Install dependencies
echo "📦 Installing dashboard dependencies..."
pip install -q fastapi uvicorn[standard] psutil redis

echo ""
echo "✅ Dashboard dependencies installed!"
echo ""
echo "🚀 Starting dashboard..."
echo "   URL: http://localhost:8000"
echo ""
echo "Press CTRL+C to stop the dashboard"
echo "=================================================="
echo ""

# Start dashboard
python servers/dashboard_server.py
