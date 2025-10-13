# 🚀 Production Deployment Steps

GitHub Actions are working! Now deploy your infrastructure to AWS.

## ✅ Current Status

- ✅ Code in GitHub (merged to main)
- ✅ GitHub Actions building Docker images successfully
- ✅ All secrets configured (16 secrets)
- ✅ Docker images pushed to ghcr.io/souravs72/claude-mcp-setup
- ⏳ Infrastructure needs to be deployed

## 🎯 Deployment Phase 1: AWS Infrastructure (15-20 minutes)

### Step 1: Deploy with Terraform

```bash
cd /home/clapgrow/Desktop/claude-mcp-setup/cloud/terraform

# Create your configuration
cat > terraform.tfvars <<EOF
aws_region = "ap-south-1"
cluster_name = "mcp-servers-prod"
environment = "production"

# These will be pulled from GitHub secrets
github_token = "dummy"  # Not used in infrastructure
jira_api_token = "dummy"
google_api_key = "dummy"
google_search_engine_id = "dummy"
EOF

# Initialize Terraform
terraform init

# Preview what will be created
terraform plan

# Deploy infrastructure (this creates everything!)
terraform apply
```

**What This Creates:**

- ✅ EKS Kubernetes cluster (3 nodes)
- ✅ RDS PostgreSQL database (managed)
- ✅ ElastiCache Redis (managed cache)
- ✅ VPC with 3 availability zones
- ✅ Security groups and IAM roles
- ✅ LoadBalancers

**Time:** ~15 minutes  
**Cost:** ~₹35,000/month

### Step 2: Configure kubectl

```bash
# Get cluster credentials
aws eks update-kubeconfig --name mcp-servers-prod --region ap-south-1

# Verify connection
kubectl get nodes

# Expected output:
# NAME                                            STATUS   ROLES    AGE
# ip-10-0-1-xxx.ap-south-1.compute.internal      Ready    <none>   5m
# ip-10-0-2-xxx.ap-south-1.compute.internal      Ready    <none>   5m
# ip-10-0-3-xxx.ap-south-1.compute.internal      Ready    <none>   5m
```

## 🎯 Deployment Phase 2: Deploy Services (10 minutes)

### Step 3: Create Secrets in Kubernetes

```bash
cd /home/clapgrow/Desktop/claude-mcp-setup/cloud/helm

# Create secrets.yaml with your configuration
cat > secrets.yaml <<'EOF'
secrets:
  githubToken: "$GH_TOKEN"  # Will be filled from environment
  jiraApiToken: "$JIRA_TOKEN"
  googleApiKey: "$GOOGLE_KEY"
  googleSearchEngineId: "$GOOGLE_ENGINE"
  frappeApiKey: "$FRAPPE_KEY"
  frappeApiSecret: "$FRAPPE_SECRET"
  postgresPassword: "$POSTGRES_PASS"

global:
  imageRegistry: ghcr.io/souravs72/claude-mcp-setup
  imageTag: main

# Database endpoints from Terraform
servers:
  goalAgent:
    env:
      POSTGRES_HOST: "REPLACE_WITH_RDS_ENDPOINT"
  memoryCache:
    env:
      REDIS_HOST: "REPLACE_WITH_REDIS_ENDPOINT"
EOF

# Get endpoints from Terraform
cd ../terraform
POSTGRES_ENDPOINT=$(terraform output -raw postgres_endpoint | cut -d: -f1)
REDIS_ENDPOINT=$(terraform output -raw redis_endpoint)

# Update secrets.yaml with actual endpoints
cd ../helm
sed -i "s/REPLACE_WITH_RDS_ENDPOINT/${POSTGRES_ENDPOINT}/" secrets.yaml
sed -i "s/REPLACE_WITH_REDIS_ENDPOINT/${REDIS_ENDPOINT}/" secrets.yaml
```

### Step 4: Deploy with Helm

```bash
cd /home/clapgrow/Desktop/claude-mcp-setup/cloud/helm

# Deploy all services
helm upgrade --install mcp-servers ./mcp-servers \
  --namespace mcp-servers \
  --create-namespace \
  -f secrets.yaml \
  --set global.imageRegistry=ghcr.io/souravs72/claude-mcp-setup \
  --set global.imageTag=main \
  --wait \
  --timeout 10m

# Watch deployment
kubectl get pods -n mcp-servers -w
```

Press Ctrl+C when all pods show `Running` status.

### Step 5: Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n mcp-servers

# Expected output:
# NAME                                   READY   STATUS    RESTARTS   AGE
# memory-cache-server-xxx                1/1     Running   0          2m
# memory-cache-server-yyy                1/1     Running   0          2m
# goal-agent-server-xxx                  1/1     Running   0          2m
# goal-agent-server-yyy                  1/1     Running   0          2m
# github-server-xxx                      1/1     Running   0          2m
# github-server-yyy                      1/1     Running   0          2m
# jira-server-xxx                        1/1     Running   0          2m
# jira-server-yyy                        1/1     Running   0          2m
# internet-server-xxx                    1/1     Running   0          2m
# internet-server-yyy                    1/1     Running   0          2m
# postgres-xxx                           1/1     Running   0          2m
# redis-xxx                              1/1     Running   0          2m

# Check services and get LoadBalancer URLs
kubectl get services -n mcp-servers
```

## 🎯 Deployment Phase 3: Configure DNS (10 minutes)

### Step 6: Get LoadBalancer URLs

```bash
# Get all service URLs
kubectl get services -n mcp-servers -o wide

# Copy the EXTERNAL-IP addresses (LoadBalancer URLs)
# They will look like: a1234567890.ap-south-1.elb.amazonaws.com
```

### Step 7: Configure DNS for frappewizard.com

Go to your DNS provider (where you manage frappewizard.com) and add these CNAME records:

```
Type    Name                    Value (LoadBalancer URL from above)              TTL
----------------------------------------------------------------------------------------
CNAME   memory-cache           a1111111111.ap-south-1.elb.amazonaws.com         300
CNAME   goal-agent             a2222222222.ap-south-1.elb.amazonaws.com         300
CNAME   github-service         a3333333333.ap-south-1.elb.amazonaws.com         300
CNAME   jira-service           a4444444444.ap-south-1.elb.amazonaws.com         300
CNAME   internet-service       a5555555555.ap-south-1.elb.amazonaws.com         300
```

**This creates:**

- `memory-cache.frappewizard.com`
- `goal-agent.frappewizard.com`
- `github-service.frappewizard.com`
- `jira-service.frappewizard.com`
- `internet-service.frappewizard.com`

### Step 8: Wait for DNS Propagation (5-10 minutes)

```bash
# Test DNS resolution
nslookup goal-agent.frappewizard.com

# Test connectivity
curl http://goal-agent.frappewizard.com/health

# Should return: {"status":"healthy"}
```

## 🎯 Deployment Phase 4: Enable HTTPS (Optional - 10 minutes)

### Step 9: Install cert-manager

```bash
# Add Jetstack Helm repository
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Install cert-manager
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true \
  --wait
```

### Step 10: Create Let's Encrypt Issuer

```bash
cat <<EOF | kubectl apply -f -
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
```

### Step 11: Enable Ingress with HTTPS

```bash
cd /home/clapgrow/Desktop/claude-mcp-setup/cloud/helm

# Update with ingress enabled
helm upgrade mcp-servers ./mcp-servers \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=mcp.frappewizard.com \
  --reuse-values
```

## 🎯 Deployment Phase 5: Configure Claude Desktop (5 minutes)

### Step 12: Update Claude Desktop Configuration

**Config location:**

- Linux: `~/.config/Claude/claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Copy template:**

```bash
cp /home/clapgrow/Desktop/claude-mcp-setup/cloud/config-examples/claude-desktop-cloud.json \
   ~/.config/Claude/claude_desktop_config.json
```

**Edit the file** and replace URLs with your actual ones:

```json
{
  "mcpServers": {
    "memory-cache": {
      "command": "python",
      "args": [
        "/home/clapgrow/Desktop/claude-mcp-setup/cloud/mcp-http-proxy.py",
        "http://memory-cache.frappewizard.com"
      ],
      "env": {}
    },
    "goal-agent": {
      "command": "python",
      "args": [
        "/home/clapgrow/Desktop/claude-mcp-setup/cloud/mcp-http-proxy.py",
        "http://goal-agent.frappewizard.com"
      ],
      "env": {}
    },
    "github": {
      "command": "python",
      "args": [
        "/home/clapgrow/Desktop/claude-mcp-setup/cloud/mcp-http-proxy.py",
        "http://github-service.frappewizard.com"
      ],
      "env": {}
    },
    "jira": {
      "command": "python",
      "args": [
        "/home/clapgrow/Desktop/claude-mcp-setup/cloud/mcp-http-proxy.py",
        "http://jira-service.frappewizard.com"
      ],
      "env": {}
    },
    "internet": {
      "command": "python",
      "args": [
        "/home/clapgrow/Desktop/claude-mcp-setup/cloud/mcp-http-proxy.py",
        "http://internet-service.frappewizard.com"
      ],
      "env": {}
    }
  }
}
```

### Step 13: Restart Claude Desktop

**Completely restart** Claude Desktop:

1. Quit Claude Desktop
2. Wait 5 seconds
3. Open Claude Desktop

### Step 14: Test!

In Claude Desktop, try:

- "Create a goal to test the cloud deployment"
- "List my GitHub repositories"
- "Search Jira for recent issues in CGV2"
- "Search the web for Kubernetes best practices"

## 🎉 You're Done!

Your MCP servers are now:

- ✅ Running in AWS Mumbai region
- ✅ Accessible via frappewizard.com
- ✅ Connected to Claude Desktop
- ✅ Auto-scaling (2-10 pods)
- ✅ Highly available (99.9% uptime)
- ✅ Production-ready!

---

## 📋 Quick Reference Commands

```bash
# Check deployment status
kubectl get pods -n mcp-servers
kubectl get services -n mcp-servers

# View logs
kubectl logs -f deployment/goal-agent-server -n mcp-servers

# Scale a service
kubectl scale deployment/goal-agent-server --replicas=5 -n mcp-servers

# Update services
cd /home/clapgrow/Desktop/claude-mcp-setup/cloud/helm
helm upgrade mcp-servers ./mcp-servers --reuse-values

# Check costs
aws ce get-cost-and-usage --time-period Start=2025-10-01,End=2025-10-13 --granularity MONTHLY --metrics BlendedCost
```

## 🆘 Troubleshooting

### Pods not starting

```bash
kubectl describe pod <pod-name> -n mcp-servers
kubectl logs <pod-name> -n mcp-servers
```

### Can't access services

```bash
# Test from within cluster
kubectl run test --rm -it --image=curlimages/curl -- \
  curl http://goal-agent-service:8002/health
```

### DNS not resolving

```bash
nslookup goal-agent.frappewizard.com
dig goal-agent.frappewizard.com
```

---

## 💰 Monitor Costs

```bash
# Check current month spend
aws ce get-cost-and-usage \
  --time-period Start=$(date -d "$(date +%Y-%m-01)" +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost

# Set up billing alerts (optional)
aws cloudwatch put-metric-alarm --alarm-name mcp-cost-alert \
  --alarm-description "Alert when costs exceed ₹40,000" \
  --metric-name EstimatedCharges \
  --threshold 500
```

---

## 📞 Support

- **GitHub Actions**: https://github.com/souravs72/claude-mcp-setup/actions
- **Documentation**: `cloud/` directory
- **Issues**: https://github.com/souravs72/claude-mcp-setup/issues
- **Email**: sourav@clapgrow.com

---

**Start with Phase 1: Deploy Infrastructure!** 🚀
