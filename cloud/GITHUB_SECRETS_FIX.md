# 🔧 GitHub Secrets Name Fix

## Issue: `GITHUB_` Prefix Not Allowed

GitHub Actions has a restriction: **secret names cannot start with `GITHUB_`** as this is a reserved prefix.

### Error You Might See

```
failed to set secret "GITHUB_TOKEN_PROD": HTTP 422:
Secret names must not start with GITHUB_.
```

## ✅ Solution: Updated Secret Names

We've renamed the secrets to avoid the reserved prefix:

| Old Name (❌ Doesn't work) | New Name (✅ Works) |
| -------------------------- | ------------------- |
| `GITHUB_TOKEN_PROD`        | `GH_TOKEN_PROD`     |
| `GITHUB_TOKEN_STAGING`     | `GH_TOKEN_STAGING`  |

## 📝 Updated Files

The following files have been automatically updated:

1. ✅ `cloud/setup-github-secrets.sh` - Uses `GH_TOKEN_*`
2. ✅ `.github/workflows/deploy.yml` - References updated
3. ✅ `cloud/SECRETS_SUMMARY.md` - Documentation updated
4. ✅ `cloud/verify-setup.sh` - Verification checks updated
5. ✅ `cloud/SETUP_INSTRUCTIONS.md` - Manual setup instructions updated

## 🚀 What to Do Now

Just run the setup script again - it will work now:

```bash
cd /home/clapgrow/Desktop/claude-mcp-setup/cloud
./setup-github-secrets.sh
```

The script now uses the correct secret names (`GH_TOKEN_PROD` and `GH_TOKEN_STAGING`).

## 🔍 Verify Secrets

After running the script, verify:

```bash
gh secret list -R souravs72/claude-mcp-setup
```

You should see:

- ✅ `GH_TOKEN_PROD`
- ✅ `GH_TOKEN_STAGING`
- ✅ `JIRA_API_TOKEN`
- ✅ `GOOGLE_API_KEY`
- ✅ `GOOGLE_SEARCH_ENGINE_ID`
- ✅ `FRAPPE_API_KEY`
- ✅ `FRAPPE_API_SECRET`
- ✅ And others...

## 📚 Why This Restriction?

GitHub reserves certain prefixes for internal use:

- `GITHUB_*` - Reserved for GitHub Actions context variables
- Cannot be overridden to prevent security issues

Examples of reserved GitHub variables:

- `GITHUB_TOKEN` (auto-generated for workflows)
- `GITHUB_REPOSITORY`
- `GITHUB_SHA`
- etc.

## ✅ All Fixed!

Everything is now corrected. Just run the setup script again and it will work perfectly! 🎉
