#!/bin/bash
set -e

# GitHub Secrets Setup Script
# This script sets all required secrets in your GitHub repository
# 
# Prerequisites:
# - GitHub CLI (gh) installed and authenticated
# - Run: gh auth login
#
# Usage: ./setup-github-secrets.sh

REPO="souravs72/claude-mcp-setup"

echo "========================================"
echo "Setting up GitHub Secrets"
echo "Repository: $REPO"
echo "========================================"

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

# Function to set secret
set_secret() {
    local name=$1
    local value=$2
    echo "Setting secret: $name"
    echo "$value" | gh secret set "$name" --repo "$REPO"
}

# Read secrets from local config file
CONFIG_FILE="${CONFIG_FILE:-$HOME/Desktop/claude-mcp-setup/config/mcp_settings.json}"
AWS_CREDS="${HOME}/.aws/credentials"
AWS_CONFIG="${HOME}/.aws/config"

echo "Reading secrets from local configuration..."
echo ""

# Read from mcp_settings.json
if [ -f "$CONFIG_FILE" ]; then
    GH_TOKEN=$(jq -r '.mcpServers."github-server".env.GITHUB_PERSONAL_ACCESS_TOKEN // empty' "$CONFIG_FILE")
    JIRA_TOKEN=$(jq -r '.mcpServers."jira-server".env.JIRA_API_TOKEN // empty' "$CONFIG_FILE")
    JIRA_URL=$(jq -r '.mcpServers."jira-server".env.JIRA_BASE_URL // empty' "$CONFIG_FILE")
    JIRA_EMAIL=$(jq -r '.mcpServers."jira-server".env.JIRA_EMAIL // empty' "$CONFIG_FILE")
    JIRA_PROJECT=$(jq -r '.mcpServers."jira-server".env.JIRA_PROJECT_KEY // empty' "$CONFIG_FILE")
    GOOGLE_KEY=$(jq -r '.mcpServers."internet-server".env.GOOGLE_API_KEY // empty' "$CONFIG_FILE")
    GOOGLE_ENGINE=$(jq -r '.mcpServers."internet-server".env.GOOGLE_SEARCH_ENGINE_ID // empty' "$CONFIG_FILE")
    FRAPPE_KEY=$(jq -r '.mcpServers."frappe-server".env.FRAPPE_API_KEY // empty' "$CONFIG_FILE")
    FRAPPE_SECRET=$(jq -r '.mcpServers."frappe-server".env.FRAPPE_API_SECRET // empty' "$CONFIG_FILE")
    FRAPPE_URL=$(jq -r '.mcpServers."frappe-server".env.FRAPPE_SITE_URL // empty' "$CONFIG_FILE")
fi

# Read AWS credentials
if [ -f "$AWS_CREDS" ]; then
    AWS_KEY=$(grep -A 2 "\[default\]" "$AWS_CREDS" | grep aws_access_key_id | cut -d'=' -f2 | tr -d ' ')
    AWS_SECRET=$(grep -A 2 "\[default\]" "$AWS_CREDS" | grep aws_secret_access_key | cut -d'=' -f2 | tr -d ' ')
fi

if [ -f "$AWS_CONFIG" ]; then
    AWS_REGION=$(grep -A 2 "\[default\]" "$AWS_CONFIG" | grep region | cut -d'=' -f2 | tr -d ' ')
fi

# Get AWS account ID
if command -v aws &> /dev/null && [ -n "$AWS_KEY" ]; then
    AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
fi

echo "Setting secrets..."
echo ""

# Set secrets only if they were found
[ -n "$GH_TOKEN" ] && set_secret "GH_TOKEN_PROD" "$GH_TOKEN"
[ -n "$GH_TOKEN" ] && set_secret "GH_TOKEN_STAGING" "$GH_TOKEN"
[ -n "$JIRA_TOKEN" ] && set_secret "JIRA_API_TOKEN" "$JIRA_TOKEN"
[ -n "$JIRA_URL" ] && set_secret "JIRA_BASE_URL" "$JIRA_URL"
[ -n "$JIRA_EMAIL" ] && set_secret "JIRA_EMAIL" "$JIRA_EMAIL"
[ -n "$JIRA_PROJECT" ] && set_secret "JIRA_PROJECT_KEY" "$JIRA_PROJECT"
[ -n "$GOOGLE_KEY" ] && set_secret "GOOGLE_API_KEY" "$GOOGLE_KEY"
[ -n "$GOOGLE_ENGINE" ] && set_secret "GOOGLE_SEARCH_ENGINE_ID" "$GOOGLE_ENGINE"
[ -n "$FRAPPE_KEY" ] && set_secret "FRAPPE_API_KEY" "$FRAPPE_KEY"
[ -n "$FRAPPE_SECRET" ] && set_secret "FRAPPE_API_SECRET" "$FRAPPE_SECRET"
[ -n "$FRAPPE_URL" ] && set_secret "FRAPPE_SITE_URL" "$FRAPPE_URL"
[ -n "$AWS_KEY" ] && set_secret "AWS_ACCESS_KEY_ID" "$AWS_KEY"
[ -n "$AWS_SECRET" ] && set_secret "AWS_SECRET_ACCESS_KEY" "$AWS_SECRET"
[ -n "$AWS_REGION" ] && set_secret "AWS_REGION" "$AWS_REGION"
[ -n "$AWS_ACCOUNT" ] && set_secret "AWS_ACCOUNT_ID" "$AWS_ACCOUNT"

echo ""

# PostgreSQL password (generate secure one)
POSTGRES_PASSWORD=$(openssl rand -base64 32)
set_secret "POSTGRES_PASSWORD" "$POSTGRES_PASSWORD"

echo ""
echo "========================================"
echo "✓ GitHub Secrets Setup Complete!"
echo "========================================"
echo ""
echo "Secrets set:"
echo "  ✓ GH_TOKEN_PROD"
echo "  ✓ GH_TOKEN_STAGING"
echo "  ✓ JIRA_API_TOKEN"
echo "  ✓ JIRA_BASE_URL"
echo "  ✓ JIRA_EMAIL"
echo "  ✓ JIRA_PROJECT_KEY"
echo "  ✓ GOOGLE_API_KEY"
echo "  ✓ GOOGLE_SEARCH_ENGINE_ID"
echo "  ✓ FRAPPE_API_KEY"
echo "  ✓ FRAPPE_API_SECRET"
echo "  ✓ FRAPPE_SITE_URL"
echo "  ✓ POSTGRES_PASSWORD (auto-generated)"
echo "  ✓ AWS_ACCESS_KEY_ID"
echo "  ✓ AWS_SECRET_ACCESS_KEY"
echo "  ✓ AWS_REGION"
echo "  ✓ AWS_ACCOUNT_ID"
echo ""
echo "View all secrets:"
echo "  gh secret list --repo $REPO"
echo ""

