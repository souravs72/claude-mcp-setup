#!/bin/bash
set -e

echo "========================================"
echo "🔒 Safe Push to GitHub"
echo "========================================"
echo ""

# Check for accidentally exposed secrets
echo "Checking for exposed secrets..."
echo ""

ISSUES=0

# Check for actual AWS keys (not in documentation/examples)
if git grep "AKIA" 2>/dev/null | grep -v "\.md:" | grep -v "example" | grep -v "SECURITY" | grep -v "\.template" | grep -v "# AWS keys" | grep -q .; then
    echo "❌ Found AWS access key in code files!"
    git grep "AKIA" | grep -v "\.md:" | grep -v "example" | head -5
    ISSUES=1
fi

# Check for actual GitHub tokens (not format examples or validators)
if git grep "ghp_[A-Za-z0-9]{36}" 2>/dev/null | grep -v "\.md:" | grep -v "example" | grep -v "\.template" | grep -v "format" | grep -v "startswith" | grep -q .; then
    echo "❌ Found actual GitHub token in files!"
    git grep "ghp_[A-Za-z0-9]{36}" | grep -v "\.md:" | grep -v "example" | head -5
    ISSUES=1
fi

# Check for hardcoded passwords
if git grep -qi "password.*=.*['\"]" 2>/dev/null | grep -v "example\|placeholder\|YOUR_"; then
    echo "⚠️  Found potential hardcoded passwords!"
    ISSUES=1
fi

if [ $ISSUES -eq 0 ]; then
    echo "✅ No obvious secrets found in tracked files"
    echo ""
    echo "Files being pushed:"
    git diff --name-only origin/dev 2>/dev/null || git diff --name-only --staged
    echo ""
    read -p "Push to GitHub? (yes/no): " confirm
    
    if [ "$confirm" = "yes" ]; then
        echo ""
        echo "Pushing to GitHub..."
        git push origin dev
        echo ""
        echo "✅ Pushed successfully!"
        echo ""
        echo "Next steps:"
        echo "1. Set GitHub secrets: ./cloud/setup-github-secrets.sh"
        echo "2. Merge dev to main to trigger deployment"
    else
        echo "Push cancelled."
    fi
else
    echo ""
    echo "========================================"
    echo "❌ CANNOT PUSH - SECRETS DETECTED!"
    echo "========================================"
    echo ""
    echo "Please remove secrets from files and try again."
    echo ""
    echo "See cloud/SECURITY.md for guidance."
    exit 1
fi

