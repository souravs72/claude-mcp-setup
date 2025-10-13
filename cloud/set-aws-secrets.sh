#!/bin/bash
set -e

# Quick script to set AWS secrets to GitHub
# This uses your local AWS configuration

REPO="souravs72/claude-mcp-setup"

echo "========================================"
echo "Setting AWS Secrets to GitHub"
echo "Repository: $REPO"
echo "========================================"
echo ""

# Check if gh is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed"
    echo "Install it: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub CLI"
    echo "Run: gh auth login"
    exit 1
fi

echo "✓ GitHub CLI is ready"
echo ""

# Get AWS credentials from local config
AWS_CREDS="${HOME}/.aws/credentials"
AWS_CONFIG="${HOME}/.aws/config"

if [ -f "$AWS_CREDS" ]; then
    AWS_ACCESS_KEY_ID=$(grep -A 2 "\[default\]" "$AWS_CREDS" | grep aws_access_key_id | cut -d'=' -f2 | tr -d ' ')
    AWS_SECRET_ACCESS_KEY=$(grep -A 2 "\[default\]" "$AWS_CREDS" | grep aws_secret_access_key | cut -d'=' -f2 | tr -d ' ')
else
    echo "❌ AWS credentials not found at ~/.aws/credentials"
    exit 1
fi

if [ -f "$AWS_CONFIG" ]; then
    AWS_REGION=$(grep -A 2 "\[default\]" "$AWS_CONFIG" | grep region | cut -d'=' -f2 | tr -d ' ')
else
    AWS_REGION="ap-south-1"
fi

# Get AWS account ID
if command -v aws &> /dev/null; then
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "unknown")
else
    AWS_ACCOUNT_ID="unknown"
fi

echo "Setting AWS secrets..."
echo ""

# Set secrets
echo "Setting AWS_ACCESS_KEY_ID..."
echo "$AWS_ACCESS_KEY_ID" | gh secret set AWS_ACCESS_KEY_ID --repo "$REPO"

echo "Setting AWS_SECRET_ACCESS_KEY..."
echo "$AWS_SECRET_ACCESS_KEY" | gh secret set AWS_SECRET_ACCESS_KEY --repo "$REPO"

echo "Setting AWS_REGION..."
echo "$AWS_REGION" | gh secret set AWS_REGION --repo "$REPO"

echo "Setting AWS_ACCOUNT_ID..."
echo "$AWS_ACCOUNT_ID" | gh secret set AWS_ACCOUNT_ID --repo "$REPO"

echo ""
echo "========================================"
echo "✓ AWS Secrets Set Successfully!"
echo "========================================"
echo ""
echo "Secrets set:"
echo "  ✓ AWS_ACCESS_KEY_ID"
echo "  ✓ AWS_SECRET_ACCESS_KEY"
echo "  ✓ AWS_REGION (${AWS_REGION})"
echo "  ✓ AWS_ACCOUNT_ID (${AWS_ACCOUNT_ID})"
echo ""
echo "Verify secrets:"
echo "  gh secret list --repo $REPO"
echo ""
echo "You can now deploy to AWS!"
echo "  ./deploy.sh production aws"
echo ""

