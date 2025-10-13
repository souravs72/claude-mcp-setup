#!/bin/bash
set -e

# Cloud Deployment Script for MCP Servers
# Usage: ./deploy.sh [environment] [cloud-provider]
# Example: ./deploy.sh production aws

ENVIRONMENT="${1:-production}"
CLOUD_PROVIDER="${2:-aws}"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "========================================"
echo "MCP Servers Cloud Deployment"
echo "========================================"
echo "Environment: $ENVIRONMENT"
echo "Cloud Provider: $CLOUD_PROVIDER"
echo "========================================"

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

check_prereqs() {
    log_info "Checking prerequisites..."
    
    local missing=0
    
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Please install kubectl."
        missing=1
    fi
    
    if ! command -v helm &> /dev/null; then
        log_error "helm not found. Please install Helm."
        missing=1
    fi
    
    if ! command -v terraform &> /dev/null; then
        log_warn "terraform not found. Terraform deployment will be skipped."
    fi
    
    if ! command -v docker &> /dev/null; then
        log_error "docker not found. Please install Docker."
        missing=1
    fi
    
    if [ $missing -eq 1 ]; then
        log_error "Missing required tools. Please install them and try again."
        exit 1
    fi
    
    log_info "All prerequisites satisfied"
}

setup_aws() {
    log_info "Setting up AWS environment..."
    
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found. Please install it."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Run 'aws configure'"
        exit 1
    fi
    
    export AWS_REGION="${AWS_REGION:-us-east-1}"
    export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    export REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
    
    log_info "AWS Account ID: $AWS_ACCOUNT_ID"
    log_info "AWS Region: $AWS_REGION"
    log_info "ECR Registry: $REGISTRY"
}

setup_gcp() {
    log_info "Setting up GCP environment..."
    
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI not found. Please install it."
        exit 1
    fi
    
    export GCP_PROJECT="${GCP_PROJECT:-$(gcloud config get-value project)}"
    export GCP_REGION="${GCP_REGION:-us-central1}"
    export REGISTRY="gcr.io/${GCP_PROJECT}"
    
    log_info "GCP Project: $GCP_PROJECT"
    log_info "GCP Region: $GCP_REGION"
    log_info "GCR Registry: $REGISTRY"
}

deploy_infrastructure() {
    log_info "Deploying infrastructure with Terraform..."
    
    cd "$SCRIPT_DIR/terraform"
    
    if [ ! -f "terraform.tfvars" ]; then
        log_warn "terraform.tfvars not found. Please create it with your configuration."
        log_info "See terraform.tfvars.example for reference."
        return
    fi
    
    terraform init
    terraform plan -out=tfplan
    
    read -p "Apply Terraform plan? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        terraform apply tfplan
        log_info "Infrastructure deployed successfully"
    else
        log_warn "Terraform apply skipped"
    fi
    
    cd "$PROJECT_ROOT"
}

build_and_push_images() {
    log_info "Building and pushing Docker images..."
    
    cd "$PROJECT_ROOT"
    
    # Login to registry
    if [ "$CLOUD_PROVIDER" = "aws" ]; then
        aws ecr get-login-password --region $AWS_REGION | \
            docker login --username AWS --password-stdin $REGISTRY
        
        # Create ECR repositories
        for server in base memory-cache goal-agent github jira internet; do
            aws ecr create-repository --repository-name mcp-servers/${server} 2>/dev/null || true
        done
    elif [ "$CLOUD_PROVIDER" = "gcp" ]; then
        gcloud auth configure-docker
    fi
    
    # Build images
    log_info "Building Docker images..."
    cd "$SCRIPT_DIR/docker"
    ./build-all.sh
    
    # Tag and push
    for server in memory-cache goal-agent github jira internet; do
        log_info "Pushing ${server}..."
        docker tag mcp-servers/${server}:latest ${REGISTRY}/mcp-servers/${server}:latest
        docker push ${REGISTRY}/mcp-servers/${server}:latest
    done
    
    log_info "All images pushed successfully"
}

deploy_kubernetes() {
    log_info "Deploying to Kubernetes with Helm..."
    
    cd "$SCRIPT_DIR/helm"
    
    # Check if secrets.yaml exists
    if [ ! -f "secrets.yaml" ]; then
        log_warn "secrets.yaml not found. Creating from template..."
        cat > secrets.yaml <<EOF
secrets:
  githubToken: "REPLACE_WITH_YOUR_TOKEN"
  jiraApiToken: "REPLACE_WITH_YOUR_TOKEN"
  googleApiKey: "REPLACE_WITH_YOUR_KEY"
  googleSearchEngineId: "REPLACE_WITH_YOUR_ID"
  postgresPassword: "$(openssl rand -base64 32)"

global:
  imageRegistry: ${REGISTRY}/mcp-servers
  imageTag: latest
EOF
        log_warn "Please edit secrets.yaml with your actual credentials"
        return
    fi
    
    # Deploy with Helm
    helm upgrade --install mcp-servers ./mcp-servers \
        --namespace mcp-servers \
        --create-namespace \
        -f secrets.yaml \
        --wait \
        --timeout 10m
    
    log_info "Kubernetes deployment complete"
    
    # Show service URLs
    echo ""
    log_info "Getting service URLs..."
    kubectl get services -n mcp-servers
}

verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check pod status
    kubectl get pods -n mcp-servers
    
    echo ""
    log_info "Waiting for all pods to be ready..."
    kubectl wait --for=condition=ready pod --all -n mcp-servers --timeout=300s
    
    # Test health endpoints
    echo ""
    log_info "Testing health endpoints..."
    for service in memory-cache goal-agent github jira internet; do
        log_info "Testing ${service}-service..."
        kubectl run test-${service} --rm -i --restart=Never \
            --image=curlimages/curl:latest \
            -- curl -f http://${service}-service:800X/health || log_warn "${service} health check failed"
    done
    
    echo ""
    log_info "Deployment verification complete!"
}

print_next_steps() {
    echo ""
    echo "========================================"
    echo "Deployment Complete! 🎉"
    echo "========================================"
    echo ""
    echo "Next steps:"
    echo "1. Get service URLs:"
    echo "   kubectl get services -n mcp-servers"
    echo ""
    echo "2. Configure Claude Desktop:"
    echo "   See: ${SCRIPT_DIR}/CLOUD_DEPLOYMENT_GUIDE.md"
    echo ""
    echo "3. Set up custom domain (optional):"
    echo "   Point your DNS to the LoadBalancer URLs"
    echo ""
    echo "4. Enable monitoring:"
    echo "   helm install prometheus prometheus-community/kube-prometheus-stack"
    echo ""
    echo "5. Test the deployment:"
    echo "   ./test-deployment.sh"
    echo ""
    echo "For detailed instructions, see:"
    echo "  ${SCRIPT_DIR}/CLOUD_DEPLOYMENT_GUIDE.md"
    echo ""
}

# Main execution
main() {
    check_prereqs
    
    if [ "$CLOUD_PROVIDER" = "aws" ]; then
        setup_aws
    elif [ "$CLOUD_PROVIDER" = "gcp" ]; then
        setup_gcp
    else
        log_error "Unsupported cloud provider: $CLOUD_PROVIDER"
        exit 1
    fi
    
    # Prompt for confirmation
    echo ""
    read -p "Deploy infrastructure with Terraform? (yes/no): " deploy_infra
    if [ "$deploy_infra" = "yes" ] && command -v terraform &> /dev/null; then
        deploy_infrastructure
    fi
    
    echo ""
    read -p "Build and push Docker images? (yes/no): " build_images
    if [ "$build_images" = "yes" ]; then
        build_and_push_images
    fi
    
    echo ""
    read -p "Deploy to Kubernetes? (yes/no): " deploy_k8s
    if [ "$deploy_k8s" = "yes" ]; then
        deploy_kubernetes
        verify_deployment
    fi
    
    print_next_steps
}

# Run main
main

