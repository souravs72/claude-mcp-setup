# ☁️ Cloud Deployment Files

Complete cloud-native setup for **souravs72/claude-mcp-setup** on domain **frappewizard.com**.

## 📁 What's Here

```
cloud/
├── 📘 SETUP_INSTRUCTIONS.md       # START HERE! Complete setup guide
├── 🔐 SECRETS_SUMMARY.md          # All secrets & credentials
├── 🌐 UPDATE_DNS.md               # DNS configuration for frappewizard.com
├── ⚡ QUICK_START.md               # 30-minute deployment
├── 📖 CLOUD_DEPLOYMENT_GUIDE.md   # Comprehensive production guide
│
├── 🚀 deploy.sh                    # Automated deployment script
├── 🔐 setup-github-secrets.sh     # GitHub secrets automation
├── ✅ verify-setup.sh              # Verify everything is ready
├── 🔌 mcp-http-proxy.py           # Claude Desktop connector
├── 🔧 Makefile                     # Quick commands
│
├── kubernetes/                     # Raw K8s manifests
├── helm/mcp-servers/              # Helm chart (recommended)
├── terraform/                      # Infrastructure as Code
├── docker/                         # Production Dockerfiles
└── config-examples/                # Claude Desktop configs
```

## 🚀 Quick Start (5 Steps)

### 1. Set Up GitHub Secrets

```bash
# Install GitHub CLI
sudo apt install gh  # or: brew install gh

# Authenticate
gh auth login

# Run automated setup
./setup-github-secrets.sh
```

### 2. Verify Setup

```bash
./verify-setup.sh
```

### 3. Deploy to AWS

```bash
# When you have AWS credentials
./deploy.sh production aws
```

### 4. Configure DNS

Point your **frappewizard.com** subdomains to LoadBalancers:

See [UPDATE_DNS.md](UPDATE_DNS.md)

### 5. Update Claude Desktop

Use config from `config-examples/claude-desktop-cloud.json`

Done! 🎉

## 📚 Documentation

| Document                                                   | Purpose                           |
| ---------------------------------------------------------- | --------------------------------- |
| **[SETUP_INSTRUCTIONS.md](SETUP_INSTRUCTIONS.md)**         | Complete setup guide (START HERE) |
| **[SECRETS_SUMMARY.md](SECRETS_SUMMARY.md)**               | All secrets & credentials         |
| **[UPDATE_DNS.md](UPDATE_DNS.md)**                         | DNS setup for frappewizard.com    |
| **[QUICK_START.md](QUICK_START.md)**                       | 30-minute quick deployment        |
| **[CLOUD_DEPLOYMENT_GUIDE.md](CLOUD_DEPLOYMENT_GUIDE.md)** | Comprehensive guide               |

## 🔐 Secrets Setup

Your secrets are already extracted from `config/mcp_settings.json`:

- ✅ GitHub token: `your github token`
- ✅ Jira credentials for clapgrow.atlassian.net
- ✅ Google API key and search engine ID
- ✅ Frappe API credentials
- ⏳ AWS credentials (add when ready)

**Run:** `./setup-github-secrets.sh` to set all secrets automatically!

## 🌐 Domain Configuration

**Your domain:** frappewizard.com

**Subdomains:**

- `memory-cache.frappewizard.com`
- `goal-agent.frappewizard.com`
- `github-service.frappewizard.com`
- `jira-service.frappewizard.com`
- `internet-service.frappewizard.com`

Or use: `mcp.frappewizard.com` with ingress

## 🛠️ Useful Commands

```bash
# Deploy everything
make deploy

# Build Docker images
make build

# Deploy with Helm
make install

# Check status
make status

# View logs
make logs SERVICE=goal-agent

# Scale services
make scale SERVICE=goal-agent REPLICAS=5

# Set up monitoring
make monitoring

# Destroy everything
make destroy
```

## 🎯 Deployment Options

### Automated (Recommended)

```bash
./deploy.sh production aws
```

One command does everything!

### Manual Step-by-Step

```bash
# 1. Infrastructure
cd terraform && terraform apply

# 2. Images
cd ../docker && ./build-all.sh

# 3. Deploy
cd ../helm && helm install mcp-servers ./mcp-servers
```

### Using Makefile

```bash
make deploy ENVIRONMENT=production CLOUD_PROVIDER=aws
```

## 📊 What Gets Deployed

### Infrastructure (Terraform)

- ✅ EKS Kubernetes cluster
- ✅ RDS PostgreSQL database
- ✅ ElastiCache Redis
- ✅ VPC & networking
- ✅ Load balancers
- ✅ Security groups

### Services (Kubernetes/Helm)

- ✅ Memory Cache (2 replicas)
- ✅ Goal Agent (2 replicas)
- ✅ GitHub (2 replicas)
- ✅ Jira (2 replicas)
- ✅ Internet (2 replicas)

### Features

- ✅ Auto-healing
- ✅ Auto-scaling (2-10 pods)
- ✅ Health checks
- ✅ Rolling updates
- ✅ Zero-downtime deploys

## 💰 Costs

- **Production**: ~$450/month (AWS us-east-1)
- **Development**: ~$150/month (smaller instances)

Breakdown:

- EKS cluster: $73
- EC2 instances: $90
- RDS PostgreSQL: $60
- ElastiCache Redis: $15
- Load Balancers: $125
- Data transfer: $90

## 🔄 CI/CD Pipeline

Automatic deployment via GitHub Actions:

- Push to `dev` → deploys to staging
- Push to `main` → deploys to production

Already configured! Just push and it deploys.

## 📞 Support

- **Repository**: https://github.com/souravs72/claude-mcp-setup
- **Issues**: https://github.com/souravs72/claude-mcp-setup/issues
- **Email**: sourav@clapgrow.com
- **Docs**: See documentation files above

## ✅ Pre-Flight Checklist

Before deploying:

- [ ] GitHub secrets set (`./setup-github-secrets.sh`)
- [ ] AWS credentials configured
- [ ] `kubectl`, `helm`, `terraform` installed
- [ ] Docker installed and running
- [ ] Domain ready (frappewizard.com)
- [ ] Run verification: `./verify-setup.sh`

## 🎯 Next Steps

1. **Run verification**

   ```bash
   ./verify-setup.sh
   ```

2. **Set GitHub secrets**

   ```bash
   ./setup-github-secrets.sh
   ```

3. **Add AWS credentials** (when ready)

   ```bash
   gh secret set AWS_ACCESS_KEY_ID -R souravs72/claude-mcp-setup
   gh secret set AWS_SECRET_ACCESS_KEY -R souravs72/claude-mcp-setup
   ```

4. **Deploy!**

   ```bash
   ./deploy.sh production aws
   ```

5. **Configure DNS**

   - See [UPDATE_DNS.md](UPDATE_DNS.md)

6. **Update Claude Desktop**
   - Use `config-examples/claude-desktop-cloud.json`

---

**Everything is configured for your setup!** 🎉

Domain: **frappewizard.com** | Repo: **souravs72/claude-mcp-setup**
