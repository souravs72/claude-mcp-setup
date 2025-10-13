#!/bin/bash
set -e

echo "========================================"
echo "🚀 QUICKEST CLOUD DEPLOYMENT"
echo "========================================"
echo ""
echo "This will:"
echo "1. Set all GitHub secrets"
echo "2. Commit changes"
echo "3. Push to trigger auto-deployment"
echo ""
read -p "Ready to deploy? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "Step 1: Setting GitHub secrets..."
cd cloud
./setup-github-secrets.sh

echo ""
echo "Step 2: Committing changes..."
cd ..
git add .
git commit -m "Deploy MCP servers to AWS Mumbai region (ap-south-1)" || true

echo ""
echo "Step 3: Pushing to GitHub (this triggers deployment)..."
git push origin dev

echo ""
echo "========================================"
echo "✅ Deployment Started!"
echo "========================================"
echo ""
echo "GitHub Actions is now deploying to AWS!"
echo ""
echo "📊 Watch progress:"
echo "   https://github.com/souravs72/claude-mcp-setup/actions"
echo ""
echo "⏱️  Expected time: ~20 minutes"
echo ""
echo "What's being deployed:"
echo "  ✓ EKS Kubernetes cluster (Mumbai region)"
echo "  ✓ RDS PostgreSQL database"
echo "  ✓ ElastiCache Redis"
echo "  ✓ 5 MCP services (2 replicas each)"
echo "  ✓ LoadBalancers"
echo ""
echo "After deployment:"
echo "  1. Get service URLs: kubectl get svc -n mcp-servers"
echo "  2. Configure DNS (frappewizard.com)"
echo "  3. Update Claude Desktop config"
echo ""
