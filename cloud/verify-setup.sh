#!/bin/bash
set -e

# Setup Verification Script
# Checks that everything is configured correctly before deployment

echo "========================================"
echo "MCP Cloud Setup Verification"
echo "========================================"
echo ""

REPO="souravs72/claude-mcp-setup"
DOMAIN="frappewizard.com"
ERRORS=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ERRORS=$((ERRORS + 1))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo "Checking prerequisites..."
echo ""

# Check GitHub CLI
if command -v gh &> /dev/null; then
    check_pass "GitHub CLI (gh) installed"
else
    check_fail "GitHub CLI (gh) not installed"
    echo "  Install: https://cli.github.com/"
fi

# Check kubectl
if command -v kubectl &> /dev/null; then
    check_pass "kubectl installed"
else
    check_warn "kubectl not installed (needed for deployment)"
fi

# Check helm
if command -v helm &> /dev/null; then
    check_pass "helm installed"
else
    check_warn "helm not installed (needed for deployment)"
fi

# Check terraform
if command -v terraform &> /dev/null; then
    check_pass "terraform installed"
else
    check_warn "terraform not installed (needed for infrastructure)"
fi

# Check docker
if command -v docker &> /dev/null; then
    check_pass "docker installed"
else
    check_warn "docker not installed (needed for building images)"
fi

# Check AWS CLI
if command -v aws &> /dev/null; then
    check_pass "AWS CLI installed"
else
    check_warn "AWS CLI not installed (needed for AWS deployment)"
fi

echo ""
echo "Checking GitHub configuration..."
echo ""

# Check gh auth
if gh auth status &> /dev/null; then
    check_pass "GitHub CLI authenticated"
else
    check_fail "GitHub CLI not authenticated"
    echo "  Run: gh auth login"
fi

# Check secrets
if command -v gh &> /dev/null && gh auth status &> /dev/null; then
    echo ""
    echo "Checking GitHub secrets..."
    echo ""
    
    REQUIRED_SECRETS=(
        "GH_TOKEN_PROD"
        "JIRA_API_TOKEN"
        "GOOGLE_API_KEY"
        "GOOGLE_SEARCH_ENGINE_ID"
    )
    
    for secret in "${REQUIRED_SECRETS[@]}"; do
        if gh secret list -R $REPO 2>/dev/null | grep -q "^$secret"; then
            check_pass "Secret $secret is set"
        else
            check_fail "Secret $secret is missing"
        fi
    done
    
    if gh secret list -R $REPO 2>/dev/null | grep -q "^AWS_ACCESS_KEY_ID"; then
        check_pass "AWS credentials are set"
    else
        check_warn "AWS credentials not set (add them when ready)"
    fi
fi

echo ""
echo "Checking configuration files..."
echo ""

# Check if setup script exists
if [ -f "cloud/setup-github-secrets.sh" ]; then
    check_pass "GitHub secrets setup script exists"
    if [ -x "cloud/setup-github-secrets.sh" ]; then
        check_pass "Setup script is executable"
    else
        check_fail "Setup script is not executable"
        echo "  Run: chmod +x cloud/setup-github-secrets.sh"
    fi
else
    check_fail "Setup script not found"
fi

# Check if proxy script exists
if [ -f "cloud/mcp-http-proxy.py" ]; then
    check_pass "HTTP proxy script exists"
    if [ -x "cloud/mcp-http-proxy.py" ]; then
        check_pass "Proxy script is executable"
    else
        check_warn "Proxy script is not executable (will work with python command)"
    fi
else
    check_fail "Proxy script not found"
fi

# Check helm charts
if [ -f "cloud/helm/mcp-servers/Chart.yaml" ]; then
    check_pass "Helm chart exists"
    
    # Check if Chart.yaml has correct repo
    if grep -q "souravs72/claude-mcp-setup" cloud/helm/mcp-servers/Chart.yaml; then
        check_pass "Chart.yaml has correct repository"
    else
        check_fail "Chart.yaml repository not updated"
    fi
else
    check_fail "Helm chart not found"
fi

# Check terraform
if [ -f "cloud/terraform/main.tf" ]; then
    check_pass "Terraform configuration exists"
else
    check_fail "Terraform configuration not found"
fi

# Check domain configuration
if grep -r "frappewizard.com" cloud/ &> /dev/null; then
    check_pass "Domain (frappewizard.com) configured"
else
    check_warn "Domain references may need updating"
fi

echo ""
echo "========================================"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "You're ready to deploy!"
    echo ""
    echo "Next steps:"
    echo "  1. Set GitHub secrets: ./cloud/setup-github-secrets.sh"
    echo "  2. Configure AWS credentials (when ready)"
    echo "  3. Deploy: ./cloud/deploy.sh production aws"
else
    echo -e "${RED}✗ Found $ERRORS error(s)${NC}"
    echo ""
    echo "Please fix the errors above before deploying."
fi
echo "========================================"
