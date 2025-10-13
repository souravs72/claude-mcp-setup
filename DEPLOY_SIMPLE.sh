#!/bin/bash
set -e

echo "=========================================
🚀 Simple AWS Deployment
========================================="
echo ""
echo "This deploys to AWS Mumbai region (ap-south-1)"
echo ""
echo "What will be created:"
echo "  • EKS Kubernetes cluster (3 nodes)"
echo "  • RDS PostgreSQL database"
echo "  • ElastiCache Redis"
echo "  • VPC & networking"
echo "  • LoadBalancers"
echo ""
echo "Cost: ~₹35,000/month (~$450/month)"
echo "Time: ~15 minutes"
echo ""
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cancelled."
    exit 0
fi

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo ""
echo "Building deployment container..."
docker build -t mcp-deployer -f cloud/Dockerfile.deployer cloud/ -q

echo ""
echo "=========================================
Phase 1: Deploy Infrastructure with Terraform
========================================="

# Run Terraform in container
docker run --rm \
    -v "$(pwd):/workspace" \
    -v "$HOME/.aws:/root/.aws:ro" \
    -e AWS_REGION=ap-south-1 \
    --workdir /workspace/cloud/terraform \
    mcp-deployer \
    bash -c '
# Create terraform.tfvars
cat > terraform.tfvars <<TFEOF
aws_region = "ap-south-1"
cluster_name = "mcp-servers-prod"
environment = "production"
github_token = "placeholder"
jira_api_token = "placeholder"
google_api_key = "placeholder"
google_search_engine_id = "placeholder"
TFEOF

echo "Initializing Terraform..."
terraform init

echo ""
echo "Planning infrastructure..."
terraform plan -out=tfplan

echo ""
echo "Applying infrastructure..."
terraform apply -auto-approve tfplan

echo ""
echo "✅ Infrastructure deployed!"
'

if [ $? -ne 0 ]; then
    echo "❌ Infrastructure deployment failed"
    exit 1
fi

echo ""
echo "=========================================
Phase 2: Deploy Services with Helm
========================================="

# Configure kubectl and deploy services
docker run --rm \
    -v "$(pwd):/workspace" \
    -v "$HOME/.aws:/root/.aws:ro" \
    -v "$HOME/.kube:/root/.kube" \
    -e AWS_REGION=ap-south-1 \
    --workdir /workspace/cloud \
    mcp-deployer \
    bash -c '
echo "Configuring kubectl..."
aws eks update-kubeconfig --name mcp-servers-prod --region ap-south-1

echo ""
echo "Checking cluster..."
kubectl get nodes

echo ""
echo "Deploying services with Helm..."
cd helm

helm upgrade --install mcp-servers ./mcp-servers \
    --namespace mcp-servers \
    --create-namespace \
    --set global.imageRegistry=ghcr.io/souravs72/claude-mcp-setup \
    --set global.imageTag=main \
    --wait \
    --timeout 10m

echo ""
echo "✅ Services deployed!"
echo ""
echo "Pods:"
kubectl get pods -n mcp-servers

echo ""
echo "Services:"
kubectl get services -n mcp-servers
'

echo ""
echo "=========================================
✅ DEPLOYMENT COMPLETE!
========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Get LoadBalancer URLs:"
echo "   kubectl get services -n mcp-servers"
echo ""
echo "2. Configure DNS for frappewizard.com:"
echo "   See: cloud/UPDATE_DNS.md"
echo ""
echo "3. Update Claude Desktop:"
echo "   cp cloud/config-examples/claude-desktop-cloud.json ~/.config/Claude/"
echo ""
echo "4. Test in Claude Desktop!"
echo ""

