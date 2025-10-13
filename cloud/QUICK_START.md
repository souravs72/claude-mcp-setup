# ⚡ Quick Start - Cloud Deployment

Get your MCP servers running in the cloud in **30 minutes**.

## Prerequisites

- AWS account (or GCP/Azure)
- `kubectl`, `helm`, `terraform`, `docker` installed
- `aws-cli` configured with credentials

## Option 1: Automated Deployment (Recommended)

```bash
cd cloud

# Run the automated deployment script
./deploy.sh production aws

# Follow the prompts:
# 1. Deploy infrastructure? → yes
# 2. Build and push images? → yes
# 3. Deploy to Kubernetes? → yes
```

That's it! The script will:

- ✅ Create EKS cluster, RDS, ElastiCache
- ✅ Build and push Docker images
- ✅ Deploy with Helm
- ✅ Verify deployment

## Option 2: Manual Deployment

### Step 1: Deploy Infrastructure (10 min)

```bash
cd cloud/terraform

# Create your configuration
cat > terraform.tfvars <<EOF
aws_region              = "us-east-1"
cluster_name            = "mcp-servers-prod"
environment             = "production"
github_token            = "ghp_your_token"
jira_api_token          = "your_jira_token"
google_api_key          = "your_google_key"
google_search_engine_id = "your_search_id"
EOF

# Deploy
terraform init
terraform apply

# Configure kubectl
aws eks update-kubeconfig --name mcp-servers-prod --region us-east-1
```

### Step 2: Build Images (5 min)

```bash
cd cloud/docker

# Build all images
./build-all.sh

# Get your registry URL
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export REGISTRY=${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $REGISTRY

# Create repositories
for server in base memory-cache goal-agent github jira internet; do
  aws ecr create-repository --repository-name mcp-servers/${server} || true
done

# Tag and push
for server in memory-cache goal-agent github jira internet; do
  docker tag mcp-servers/${server}:latest ${REGISTRY}/mcp-servers/${server}:latest
  docker push ${REGISTRY}/mcp-servers/${server}:latest
done
```

### Step 3: Deploy to Kubernetes (10 min)

```bash
cd cloud/helm

# Create secrets
cat > secrets.yaml <<EOF
secrets:
  githubToken: "ghp_your_token"
  jiraApiToken: "your_jira_token"
  googleApiKey: "your_google_key"
  googleSearchEngineId: "your_search_id"
  postgresPassword: "$(openssl rand -base64 32)"

global:
  imageRegistry: ${REGISTRY}/mcp-servers
  imageTag: latest
EOF

# Deploy
helm install mcp-servers ./mcp-servers \
  --namespace mcp-servers \
  --create-namespace \
  -f secrets.yaml \
  --wait

# Verify
kubectl get pods -n mcp-servers
kubectl get services -n mcp-servers
```

### Step 4: Configure Claude Desktop (5 min)

```bash
# Get service URLs
kubectl get services -n mcp-servers

# Copy proxy script
cp cloud/mcp-http-proxy.py ~/mcp-http-proxy.py
chmod +x ~/mcp-http-proxy.py

# Update Claude Desktop config
# Location: ~/.config/Claude/claude_desktop_config.json (Linux)
#           ~/Library/Application Support/Claude/claude_desktop_config.json (macOS)
```

Add to your config:

```json
{
  "mcpServers": {
    "goal-agent": {
      "command": "python",
      "args": [
        "/home/yourusername/mcp-http-proxy.py",
        "http://YOUR_LOADBALANCER_URL:8002"
      ],
      "env": {}
    }
  }
}
```

**Replace `YOUR_LOADBALANCER_URL` with the actual URL from `kubectl get services`**

### Step 5: Test (2 min)

1. **Restart Claude Desktop** completely (Quit + Reopen)
2. Try: "Create a goal to test the cloud deployment"
3. If it works, you're done! 🎉

## Troubleshooting

### Pods not starting

```bash
kubectl describe pod <pod-name> -n mcp-servers
kubectl logs <pod-name> -n mcp-servers
```

### Can't connect from Claude

1. Check service URLs: `kubectl get services -n mcp-servers`
2. Test health: `curl http://YOUR_URL:8002/health`
3. Check proxy logs: `cat /tmp/mcp-http-proxy.log`

### Permission denied

```bash
# Fix kubectl permissions
aws eks update-kubeconfig --name mcp-servers-prod --region us-east-1

# Fix Docker permissions
sudo usermod -aG docker $USER
newgrp docker
```

## What's Next?

- 📊 [Set up monitoring](CLOUD_DEPLOYMENT_GUIDE.md#monitoring--observability)
- 🔒 [Configure TLS/SSL](CLOUD_DEPLOYMENT_GUIDE.md#configure-ingress-with-tls)
- 🚀 [Enable auto-scaling](CLOUD_DEPLOYMENT_GUIDE.md#enable-auto-scaling)
- 💰 [Optimize costs](CLOUD_DEPLOYMENT_GUIDE.md#cost-optimization)

## Support

- Full guide: [CLOUD_DEPLOYMENT_GUIDE.md](CLOUD_DEPLOYMENT_GUIDE.md)
- Issues: https://github.com/souravs72/claude-mcp-setup/issues
- Email: sourav@clapgrow.com

---

**Total time: ~30 minutes** ⏱️

**Monthly cost: ~$450** 💰 (AWS us-east-1, production setup)
