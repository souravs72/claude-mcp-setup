# 🔒 Security Best Practices

## ⚠️ NEVER Commit Secrets to Git!

This repository follows strict security practices:

### ✅ What We Do

1. **Secrets are read from local files**
   - `config/mcp_settings.json` (gitignored)
   - `~/.aws/credentials` (never in git)
   - `~/.aws/config` (never in git)

2. **Scripts read dynamically**
   - `setup-github-secrets.sh` reads from local config
   - No hardcoded secrets in any file
   - All sensitive data in `.gitignore`

3. **GitHub Secrets for CI/CD**
   - Secrets stored in GitHub repository settings
   - Never exposed in logs or code
   - Injected at runtime only

### ❌ What We Never Do

- ❌ Hardcode API keys in scripts
- ❌ Commit AWS credentials
- ❌ Expose secrets in documentation
- ❌ Store passwords in git
- ❌ Push `.env` files

## 🛡️ How Secrets Are Managed

### Local Development

```bash
# Secrets are read from:
~/.aws/credentials          # AWS keys
~/.aws/config               # AWS region
config/mcp_settings.json    # App secrets (gitignored)
```

### GitHub Actions (CI/CD)

```yaml
# Secrets are stored in GitHub and injected:
secrets:
  AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
  GH_TOKEN_PROD: ${{ secrets.GH_TOKEN_PROD }}
  # etc.
```

### Production (Kubernetes)

```bash
# Secrets created from GitHub secrets:
kubectl create secret generic mcp-secrets \
  --from-literal=github-token=$GITHUB_TOKEN \
  --from-literal=aws-key=$AWS_KEY
```

## 📝 Setup Script Security

Our `setup-github-secrets.sh` script:

```bash
# ✅ Reads from local files
CONFIG_FILE="$HOME/Desktop/claude-mcp-setup/config/mcp_settings.json"
GH_TOKEN=$(jq -r '.mcpServers."github-server".env.GITHUB_PERSONAL_ACCESS_TOKEN' "$CONFIG_FILE")

# ✅ Stores in GitHub Secrets
echo "$GH_TOKEN" | gh secret set GH_TOKEN_PROD --repo souravs72/claude-mcp-setup

# ❌ NEVER does this:
# set_secret "GH_TOKEN" "ghp_hardcoded_token_BAD"
```

## 🔍 Detecting Exposed Secrets

### GitHub Push Protection

GitHub automatically blocks pushes containing:
- AWS Access Keys
- GitHub Personal Access Tokens
- API keys
- Private keys
- OAuth tokens

If blocked:
1. Remove the secret from all files
2. Add the file to `.gitignore`
3. Rewrite git history if needed
4. Rotate the exposed credential

### Checking Locally

```bash
# Check for accidentally committed secrets
git grep -i "AKIA"  # AWS keys
git grep -i "ghp_"  # GitHub tokens
git grep -i "password"

# Check what will be committed
git diff --cached
```

## 🔄 Secret Rotation

Rotate secrets regularly:

```bash
# 1. Generate new credential
# 2. Update in source (AWS console, GitHub settings, etc.)
# 3. Update local config
# 4. Update GitHub secrets
./cloud/setup-github-secrets.sh

# 5. Verify
gh secret list -R souravs72/claude-mcp-setup
```

## 🚨 If You Accidentally Expose a Secret

1. **Immediately revoke/rotate the credential**
   - AWS: Delete access key, create new one
   - GitHub: Revoke token, create new one
   - Jira: Rotate API token

2. **Remove from git history**
   ```bash
   # Use git filter-branch or BFG Repo Cleaner
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch path/to/file" \
     --prune-empty --tag-name-filter cat -- --all
   
   # Force push
   git push origin --force --all
   ```

3. **Update GitHub secrets**
   ```bash
   ./cloud/setup-github-secrets.sh
   ```

4. **Verify no traces remain**
   ```bash
   git log -S "exposed_secret" --all
   ```

## ✅ Security Checklist

Before pushing:

- [ ] No secrets in any `.sh` script
- [ ] No secrets in any `.md` documentation
- [ ] No secrets in any `.yaml` or `.json` config
- [ ] `.gitignore` includes all secret files
- [ ] All secrets read from local files or environment
- [ ] Ran `git diff --cached` to check staged changes
- [ ] Tested scripts work with dynamic secret loading

## 📚 Resources

- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [AWS Secret Best Practices](https://docs.aws.amazon.com/general/latest/gr/aws-access-keys-best-practices.html)
- [BFG Repo Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)

---

**Remember**: If you can see it in git, so can everyone else. Keep secrets secret! 🔐

