# Setup Instructions for souravs72/claude-mcp-setup

Complete setup guide customized for your configuration.

## 📋 Prerequisites

- [x] GitHub account: **souravs72**
- [x] Repository: **claude-mcp-setup**
- [x] Domain: **frappewizard.com**
- [x] Secrets configured in mcp_settings.json
- [ ] AWS account (credentials needed)
- [ ] GitHub CLI installed
- [ ] kubectl, helm, terraform installed

## 🔐 Step 1: Set GitHub Secrets

### Automated Setup (Recommended)

```bash
# Install GitHub CLI if needed
# Ubuntu/Debian:
sudo apt install gh

# macOS:
brew install gh

# Authenticate
gh auth login

# Run the secrets setup script
cd /home/clapgrow/Desktop/claude-mcp-setup/cloud
./setup-github-secrets.sh
```

This will set all your secrets automatically!

### Manual Setup (Alternative)

If you prefer to set secrets manually:

```bash
# Note: Cannot use GITHUB_ prefix - it's reserved by GitHub


### Verify Secrets

```bash
gh secret list -R souravs72/claude-mcp-setup
```

## ☁️ Step 2: AWS Setup (When Ready)

When you have AWS credentials, add them:

```bash
# Set AWS secrets
gh secret set AWS_ACCESS_KEY_ID -R souravs72/claude-mcp-setup
gh secret set AWS_SECRET_ACCESS_KEY -R souravs72/claude-mcp-setup

# Configure AWS CLI locally
aws configure
```

## 🚀 Step 3: Deploy to Cloud

### Quick Deploy

```bash
cd /home/clapgrow/Desktop/claude-mcp-setup/cloud

# Deploy everything
./deploy.sh production aws
```

### Step-by-Step Deploy

```bash
# 1. Deploy infrastructure
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your AWS region, etc.
terraform init
terraform apply

# 2. Build and push images
cd ../docker
./build-all.sh

# Get your AWS account ID
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

# 3. Deploy with Helm
cd ../helm
cp secrets.yaml.example secrets.yaml
# Secrets are already filled from your config!

helm install mcp-servers ./mcp-servers \
  --namespace mcp-servers \
  --create-namespace \
  -f secrets.yaml \
  --set global.imageRegistry=${REGISTRY}/mcp-servers

# 4. Wait for deployment
kubectl rollout status deployment/goal-agent-server -n mcp-servers
```

## 🌐 Step 4: Configure DNS

### Get LoadBalancer URLs

```bash
kubectl get services -n mcp-servers
```

### Add DNS Records to frappewizard.com

Go to your DNS provider and add these CNAME records:

```
memory-cache.frappewizard.com  → your-loadbalancer-1.elb.amazonaws.com
goal-agent.frappewizard.com    → your-loadbalancer-2.elb.amazonaws.com
github-service.frappewizard.com → your-loadbalancer-3.elb.amazonaws.com
jira-service.frappewizard.com  → your-loadbalancer-4.elb.amazonaws.com
internet-service.frappewizard.com → your-loadbalancer-5.elb.amazonaws.com
```

See [UPDATE_DNS.md](UPDATE_DNS.md) for detailed instructions.

## 🔒 Step 5: Enable HTTPS

```bash
# Install cert-manager
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true

# Create Let's Encrypt issuer
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: sourav@clapgrow.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

# Enable ingress
helm upgrade mcp-servers ./mcp-servers \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=mcp.frappewizard.com
```

## 💻 Step 6: Configure Claude Desktop

Update your Claude Desktop config:

**Location:**

- Linux: `~/.config/Claude/claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Config:**

```json
{
  "mcpServers": {
    "goal-agent": {
      "command": "python",
      "args": [
        "/home/clapgrow/Desktop/claude-mcp-setup/cloud/mcp-http-proxy.py",
        "https://goal-agent.frappewizard.com"
      ],
      "env": {}
    },
    "github": {
      "command": "python",
      "args": [
        "/home/clapgrow/Desktop/claude-mcp-setup/cloud/mcp-http-proxy.py",
        "https://github-service.frappewizard.com"
      ],
      "env": {}
    },
    "jira": {
      "command": "python",
      "args": [
        "/home/clapgrow/Desktop/claude-mcp-setup/cloud/mcp-http-proxy.py",
        "https://jira-service.frappewizard.com"
      ],
      "env": {}
    },
    "internet": {
      "command": "python",
      "args": [
        "/home/clapgrow/Desktop/claude-mcp-setup/cloud/mcp-http-proxy.py",
        "https://internet-service.frappewizard.com"
      ],
      "env": {}
    }
  }
}
```

**Restart Claude Desktop** completely (Quit + Reopen)

## ✅ Step 7: Test

### Test in Claude Desktop

Try these commands:

- "Create a goal to test the cloud deployment"
- "List my GitHub repositories"
- "Search Jira for recent issues in CGV2"
- "Search the web for Kubernetes best practices"

### Test from Terminal

```bash
# Test health endpoints
curl https://goal-agent.frappewizard.com/health
curl https://github-service.frappewizard.com/health

# Test API
curl -X POST https://goal-agent.frappewizard.com/api/goals \
  -H "Content-Type: application/json" \
  -d '{"description": "Test goal", "priority": "high"}'
```

## 📊 Step 8: Set Up Monitoring (Optional)

```bash
# Install Prometheus + Grafana
make monitoring

# Access Grafana
make grafana
# Open http://localhost:3000
# Default: admin / prom-operator
```

## 🔄 CI/CD Pipeline

Your GitHub Actions pipeline is already configured!

**Automatic Deployment:**

- Push to `dev` branch → deploys to staging
- Push to `main` branch → deploys to production

**To trigger deployment:**

```bash
git add .
git commit -m "Deploy to cloud"
git push origin main
```

## 📚 Additional Resources

- **Quick Start**: [QUICK_START.md](QUICK_START.md)
- **Full Guide**: [CLOUD_DEPLOYMENT_GUIDE.md](CLOUD_DEPLOYMENT_GUIDE.md)
- **DNS Setup**: [UPDATE_DNS.md](UPDATE_DNS.md)
- **Migration**: [CLOUD_MIGRATION.md](../CLOUD_MIGRATION.md)

## 🆘 Troubleshooting

### Secrets not working

```bash
# Verify secrets are set
gh secret list -R souravs72/claude-mcp-setup

# Re-run setup script
./setup-github-secrets.sh
```

### Pods not starting

```bash
kubectl get pods -n mcp-servers
kubectl describe pod <pod-name> -n mcp-servers
kubectl logs <pod-name> -n mcp-servers
```

### Can't connect from Claude

1. Check DNS: `nslookup goal-agent.frappewizard.com`
2. Check services: `kubectl get svc -n mcp-servers`
3. Check proxy logs: `tail -f /tmp/mcp-http-proxy.log`

## 💰 Estimated Costs

- **Production**: ~$450/month (AWS us-east-1)
- **Development**: ~$150/month (smaller instances)

## 📞 Support

- **Issues**: https://github.com/souravs72/claude-mcp-setup/issues
- **Email**: sourav@clapgrow.com

---

**Ready to deploy?** Start with Step 1! 🚀
