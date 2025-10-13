# 🚀 START HERE - Cloud Native MCP Deployment

Complete cloud-native setup for **souravs72/claude-mcp-setup** on **frappewizard.com**

## ✅ What's Ready

Everything is configured and secure:

- ✅ **Kubernetes** manifests for all services
- ✅ **Helm** charts for easy deployment
- ✅ **Terraform** for AWS infrastructure (Mumbai region)
- ✅ **Docker** containers with all deployment tools
- ✅ **GitHub Actions** CI/CD pipeline
- ✅ **Security** - NO secrets in code!
- ✅ **Documentation** - Comprehensive guides

## 🎯 Three Ways to Deploy

### 🌟 Method 1: GitHub Actions (BEST - Truly Cloud Native!)

**Zero local tools needed!** GitHub does everything.

```bash
# Step 1: Authenticate with GitHub
gh auth login

# Step 2: Push code
git push origin dev

# Step 3: Set secrets
cd cloud
./setup-github-secrets.sh

# Step 4: Deploy (merge to main)
git checkout main
git merge dev
git push origin main

# Step 5: Watch deployment
# Open: https://github.com/souravs72/claude-mcp-setup/actions
```

**Time: ~25 minutes** (mostly automated)

### 🐳 Method 2: Docker Container

All tools in a container - only Docker needed!

```bash
# Step 1: Build deployer container
cd cloud
docker build -t mcp-deployer -f Dockerfile.deployer .

# Step 2: Set GitHub secrets
./setup-github-secrets.sh

# Step 3: Launch deployment container
./docker-deploy.sh

# Step 4: Inside container, deploy
./deploy.sh production aws
```

**Time: ~35 minutes** (5 min build + 30 min deploy)

### 🔧 Method 3: Local Tools (Not Recommended)

Install kubectl, helm, terraform locally and deploy.

**Time: ~60 minutes** (30 min setup + 30 min deploy)

## 📝 Step-by-Step Guide

### Step 1: Push to GitHub

```bash
# Authenticate (choose one):

# Option A: GitHub CLI
gh auth login
git push origin dev

# Option B: Personal Access Token
git push https://YOUR_TOKEN@github.com/souravs72/claude-mcp-setup.git dev

# Option C: SSH
git remote set-url origin git@github.com:souravs72/claude-mcp-setup.git
git push origin dev
```

### Step 2: Set GitHub Secrets

```bash
cd /home/clapgrow/Desktop/claude-mcp-setup/cloud

# Run the automated setup (reads from local config)
./setup-github-secrets.sh

# Verify
gh secret list -R souravs72/claude-mcp-setup
```

### Step 3: Deploy

**Option A: GitHub Actions (Auto)**

```bash
# Merge dev to main = automatic deployment!
git checkout main
git merge dev
git push origin main

# Watch: https://github.com/souravs72/claude-mcp-setup/actions
```

**Option B: Manual Deploy**

```bash
# Using Docker container
./docker-deploy.sh
# Then inside: ./deploy.sh production aws
```

### Step 4: Configure DNS

After deployment, point these domains to LoadBalancers:

```
memory-cache.frappewizard.com  → LoadBalancer-1
goal-agent.frappewizard.com    → LoadBalancer-2
github-service.frappewizard.com → LoadBalancer-3
jira-service.frappewizard.com  → LoadBalancer-4
internet-service.frappewizard.com → LoadBalancer-5
```

See: [cloud/UPDATE_DNS.md](cloud/UPDATE_DNS.md)

### Step 5: Update Claude Desktop

Copy config from: `cloud/config-examples/claude-desktop-cloud.json`

Update paths and URLs, then restart Claude Desktop.

## 📚 Documentation

| File                                                           | What It Is             |
| -------------------------------------------------------------- | ---------------------- |
| **[PUSH_TO_GITHUB.md](PUSH_TO_GITHUB.md)**                     | How to push safely     |
| **[cloud/SETUP_INSTRUCTIONS.md](cloud/SETUP_INSTRUCTIONS.md)** | Complete setup         |
| **[cloud/QUICK_START.md](cloud/QUICK_START.md)**               | 30-min guide           |
| **[cloud/SECURITY.md](cloud/SECURITY.md)**                     | Security practices     |
| **[cloud/UPDATE_DNS.md](cloud/UPDATE_DNS.md)**                 | DNS setup              |
| **[DEPLOY_NOW.md](DEPLOY_NOW.md)**                             | All deployment options |

## 🔐 Security

✅ **ALL scripts read secrets from local files:**

- `config/mcp_settings.json` (gitignored)
- `~/.aws/credentials` (never in git)
- GitHub Secrets (stored securely in GitHub)

✅ **NO secrets are hardcoded in any file**

✅ **GitHub push protection** will block any accidental exposure

## 🌐 Your Configuration

| Setting         | Value                         |
| --------------- | ----------------------------- |
| **GitHub**      | souravs72/claude-mcp-setup    |
| **Domain**      | frappewizard.com              |
| **AWS Region**  | ap-south-1 (Mumbai)           |
| **AWS Account** | From local AWS config         |
| **Jira**        | clapgrow.atlassian.net (CGV2) |

## 💰 Expected Costs

**Production in Mumbai:**

- ~₹35,000/month (~$450/month)
- EKS: ₹5,400
- EC2: ₹6,700
- RDS: ₹4,500
- ElastiCache: ₹1,100
- LoadBalancers: ₹9,300
- Data transfer: ₹6,700

## 🎯 Quick Commands

```bash
# Push to GitHub
gh auth login && git push origin dev

# Set GitHub secrets
cd cloud && ./setup-github-secrets.sh

# Verify setup
./verify-setup.sh

# Deploy (after push & secrets)
git checkout main && git merge dev && git push origin main

# Or use Docker container
./cloud/docker-deploy.sh
```

## 🆘 Need Help?

**If push blocked by GitHub:**

- Secrets are detected → See `cloud/SECURITY.md`
- Authentication failed → See `PUSH_TO_GITHUB.md`

**For deployment:**

- See `cloud/SETUP_INSTRUCTIONS.md`
- See `cloud/QUICK_START.md`

## ✨ What Happens Next

1. **Push to GitHub** → Code is safe (no secrets!)
2. **Set GitHub secrets** → Credentials stored securely
3. **Merge to main** → GitHub Actions auto-deploys
4. **~20 minutes later** → Infrastructure ready on AWS Mumbai!
5. **Configure DNS** → Point frappewizard.com subdomains
6. **Update Claude Desktop** → Connect to cloud services
7. **Done!** → Production-ready MCP system! 🎉

## 🚀 Recommended Flow (Fastest)

```bash
# 1. Push code
gh auth login
git push origin dev

# 2. Set secrets
cd cloud
./setup-github-secrets.sh

# 3. Trigger deployment
cd ..
git checkout main
git merge dev
git push origin main

# 4. Watch it deploy
echo "Open: https://github.com/souravs72/claude-mcp-setup/actions"

# 5. Configure DNS (see cloud/UPDATE_DNS.md)

# 6. Update Claude Desktop (see cloud/config-examples/)
```

**Total time: ~30 minutes** (mostly waiting for AWS to provision)

---

## 🎉 You're Ready!

All the hard work is done. Just push to GitHub and watch it deploy! 🚀

**Next command:**

```bash
gh auth login  # If not already authenticated
git push origin dev
```

Then: `cd cloud && ./setup-github-secrets.sh`
