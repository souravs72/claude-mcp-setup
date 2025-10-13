# ☁️ Cloud-Native Production Deployment Guide

Transform your local MCP setup into a cloud-native, production-ready system that Claude Desktop connects to seamlessly.

## 🎯 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Claude Desktop (Your Computer)                │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  MCP Proxy/Client (local stdio → HTTP gateway)             │ │
│  └────────────────────┬───────────────────────────────────────┘ │
└───────────────────────┼─────────────────────────────────────────┘
                        │
                        │ HTTPS
                        │
┌───────────────────────▼─────────────────────────────────────────┐
│                  Load Balancer / API Gateway                     │
│                    (TLS termination, auth)                       │
└───────────────────────┬─────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼────────┐
│ Memory Cache │ │ Goal Agent  │ │   GitHub     │
│   Service    │ │   Service   │ │   Service    │
│  (2 replicas)│ │ (2 replicas)│ │ (2 replicas) │
└──────┬───────┘ └──────┬──────┘ └──────────────┘
       │                │
       │         ┌──────┴──────┐
       │         │             │
┌──────▼─────┐ ┌─▼─────────┐ ┌▼────────────┐
│   Redis    │ │PostgreSQL │ │    Jira     │
│ElastiCache │ │    RDS    │ │  Internet   │
│ (managed)  │ │ (managed) │ │  Services   │
└────────────┘ └───────────┘ └─────────────┘
```

## 🚀 Quick Start (30 minutes)

### Prerequisites

- AWS account (or GCP/Azure)
- `kubectl` installed
- `helm` installed
- `terraform` installed
- Docker installed
- `aws-cli` configured

### Step 1: Deploy Infrastructure with Terraform

```bash
cd cloud/terraform

# Initialize Terraform
terraform init

# Create terraform.tfvars with your secrets
cat > terraform.tfvars <<EOF
aws_region              = "us-east-1"
cluster_name            = "mcp-servers-prod"
environment             = "production"
github_token            = "ghp_your_token_here"
jira_api_token          = "your_jira_token"
google_api_key          = "your_google_key"
google_search_engine_id = "your_search_id"
EOF

# Plan and apply
terraform plan
terraform apply

# Get cluster credentials
aws eks update-kubeconfig --region us-east-1 --name mcp-servers-prod
```

**What this creates:**

- EKS Kubernetes cluster (3 nodes)
- RDS PostgreSQL (managed database)
- ElastiCache Redis (managed cache)
- VPC with public/private subnets
- Security groups
- All necessary IAM roles

### Step 2: Build and Push Docker Images

```bash
# From project root
cd cloud/docker

# Build all images
./build-all.sh

# Tag for your registry (e.g., ECR)
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export REGISTRY=${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $REGISTRY

# Create ECR repositories
for server in base memory-cache goal-agent github jira internet; do
  aws ecr create-repository --repository-name mcp-servers/${server} || true
done

# Tag and push
for server in memory-cache goal-agent github jira internet; do
  docker tag mcp-servers/${server}:latest ${REGISTRY}/mcp-servers/${server}:latest
  docker push ${REGISTRY}/mcp-servers/${server}:latest
done
```

### Step 3: Deploy with Helm

```bash
cd cloud/helm

# Create secrets file (don't commit this!)
cat > secrets.yaml <<EOF
secrets:
  githubToken: "ghp_your_token"
  jiraApiToken: "your_jira_token"
  googleApiKey: "your_google_key"
  googleSearchEngineId: "your_search_id"
  postgresPassword: "$(terraform output -raw postgres_password)"

# Update image registry
global:
  imageRegistry: ${REGISTRY}/mcp-servers
EOF

# Install the chart
helm install mcp-servers ./mcp-servers \
  --namespace mcp-servers \
  --create-namespace \
  -f secrets.yaml \
  --set postgresql.enabled=false \
  --set servers.goalAgent.env.POSTGRES_HOST=$(terraform output -raw postgres_endpoint | cut -d: -f1) \
  --set servers.memoryCache.env.REDIS_HOST=$(terraform output -raw redis_endpoint)

# Wait for deployment
kubectl rollout status deployment/memory-cache-server -n mcp-servers
kubectl rollout status deployment/goal-agent-server -n mcp-servers
```

### Step 4: Get Service URLs

```bash
# Get LoadBalancer URLs
kubectl get services -n mcp-servers -o wide

# Example output:
# NAME                    TYPE           EXTERNAL-IP
# memory-cache-service    LoadBalancer   a1234...elb.amazonaws.com
# goal-agent-service      LoadBalancer   a5678...elb.amazonaws.com
# github-service          LoadBalancer   a9012...elb.amazonaws.com
# jira-service            LoadBalancer   a3456...elb.amazonaws.com
# internet-service        LoadBalancer   a7890...elb.amazonaws.com

# Set up custom domain (optional)
# Point your DNS to these LoadBalancers
```

### Step 5: Configure Claude Desktop for Cloud

**Update your Claude Desktop config** to use cloud endpoints:

```json
{
  "mcpServers": {
    "memory-cache": {
      "command": "mcp-http-proxy",
      "args": ["https://memory-cache.frappewizard.com"],
      "env": {}
    },
    "goal-agent": {
      "command": "mcp-http-proxy",
      "args": ["https://goal-agent.frappewizard.com"],
      "env": {}
    },
    "github": {
      "command": "mcp-http-proxy",
      "args": ["https://github-service.frappewizard.com"],
      "env": {}
    },
    "jira": {
      "command": "mcp-http-proxy",
      "args": ["https://jira-service.frappewizard.com"],
      "env": {}
    },
    "internet": {
      "command": "mcp-http-proxy",
      "args": ["https://internet-service.frappewizard.com"],
      "env": {}
    }
  }
}
```

**Note**: You'll need an MCP HTTP proxy (see HTTP Proxy Setup below).

## 🔐 HTTP Proxy for Claude Desktop

Since Claude Desktop uses stdio, we need a local proxy that converts stdio ↔ HTTP:

```bash
# Create mcp-http-proxy.py
cat > mcp-http-proxy.py <<'EOF'
#!/usr/bin/env python3
"""MCP HTTP Proxy - Converts stdio MCP to HTTP"""
import sys
import json
import requests
from typing import Any

def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"

    # Read from stdin (Claude Desktop)
    for line in sys.stdin:
        try:
            request = json.loads(line)

            # Forward to HTTP server
            response = requests.post(
                f"{base_url}/mcp",
                json=request,
                timeout=30
            )

            # Write response to stdout (Claude Desktop)
            sys.stdout.write(json.dumps(response.json()) + "\n")
            sys.stdout.flush()

        except Exception as e:
            error_response = {
                "error": str(e),
                "type": "proxy_error"
            }
            sys.stdout.write(json.dumps(error_response) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
EOF

chmod +x mcp-http-proxy.py

# Or install via pip (if available)
pip install mcp-http-proxy
```

## 🌐 Production Considerations

### 1. Use Managed Services

**AWS:**

```hcl
# Already configured in terraform/main.tf
- RDS PostgreSQL (Multi-AZ for HA)
- ElastiCache Redis (automatic failover)
- EKS (managed Kubernetes)
```

**GCP:**

```bash
# Use Cloud SQL and Memorystore
gcloud sql instances create mcp-postgres --database-version=POSTGRES_15
gcloud redis instances create mcp-redis --size=1 --region=us-central1
```

**Azure:**

```bash
# Use Azure Database for PostgreSQL and Azure Cache for Redis
az postgres flexible-server create --name mcp-postgres
az redis create --name mcp-redis --location eastus
```

### 2. Enable Auto-Scaling

```bash
# Update helm values
cat >> values-production.yaml <<EOF
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
EOF

helm upgrade mcp-servers ./mcp-servers -f values-production.yaml
```

### 3. Set Up Monitoring

```bash
# Install Prometheus + Grafana
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace

# Enable ServiceMonitors in values.yaml
monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
```

### 4. Configure Ingress with TLS

```bash
# Install cert-manager
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true

# Update helm values
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: mcp.yourdomain.com
  tls:
    - secretName: mcp-tls
      hosts:
        - mcp.yourdomain.com
```

### 5. Implement Rate Limiting

```yaml
# Add to ingress annotations
nginx.ingress.kubernetes.io/rate-limit: "100"
nginx.ingress.kubernetes.io/limit-rps: "10"
nginx.ingress.kubernetes.io/limit-connections: "20"
```

### 6. Enable Backup & Disaster Recovery

```bash
# Automated PostgreSQL backups (already enabled in Terraform)
# Retention: 7 days
# Point-in-time recovery enabled

# Redis persistence (for critical data)
# Update redis config:
save 900 1
save 300 10
appendonly yes
```

## 💰 Cost Optimization

### Development/Staging

```hcl
# terraform.tfvars for staging
instance_types = ["t3.small"]  # Smaller instances
min_size       = 1
max_size       = 3
desired_size   = 1

# Use single AZ
azs = ["us-east-1a"]
enable_nat_gateway = true
single_nat_gateway = true

# Smaller RDS instance
db_instance_class = "db.t3.micro"

# Estimated cost: $150-200/month
```

### Production

```hcl
# terraform.tfvars for production
instance_types = ["t3.medium"]
min_size       = 2
max_size       = 10
desired_size   = 3

# Multi-AZ for high availability
azs = ["us-east-1a", "us-east-1b", "us-east-1c"]

db_instance_class = "db.t3.medium"

# Estimated cost: $400-600/month
```

### Cost Breakdown (AWS, us-east-1):

| Service            | Configuration  | Monthly Cost    |
| ------------------ | -------------- | --------------- |
| EKS Cluster        | Control plane  | $73             |
| EC2 (3x t3.medium) | 24/7 on-demand | $90             |
| RDS PostgreSQL     | db.t3.medium   | $60             |
| ElastiCache Redis  | cache.t3.micro | $15             |
| LoadBalancers (5)  | Standard ALB   | $125            |
| Data Transfer      | 1TB/month      | $90             |
| **Total**          |                | **~$450/month** |

**Optimization tips:**

- Use Reserved Instances (save 30-70%)
- Use Spot Instances for non-critical workloads
- Enable auto-scaling to scale down during off-hours
- Use S3 for logs instead of EBS

## 🔄 CI/CD Pipeline

### GitHub Actions (Included)

The `.github/workflows/deploy.yml` automatically:

1. ✅ Builds Docker images on push
2. ✅ Runs tests with PostgreSQL + Redis
3. ✅ Deploys to staging on `dev` branch
4. ✅ Deploys to production on `main` branch
5. ✅ Runs smoke tests after deployment

### GitLab CI (Alternative)

```yaml
# .gitlab-ci.yml
stages:
  - build
  - test
  - deploy

build:
  stage: build
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA

deploy:production:
  stage: deploy
  only:
    - main
  script:
    - helm upgrade mcp-servers ./cloud/helm/mcp-servers
      --set global.imageTag=$CI_COMMIT_SHA
```

## 📊 Monitoring & Observability

### 1. Application Metrics

```python
# Add to each server
from prometheus_client import Counter, Histogram

request_count = Counter('mcp_requests_total', 'Total requests')
request_duration = Histogram('mcp_request_duration_seconds', 'Request duration')

@app.middleware("http")
async def metrics_middleware(request, call_next):
    request_count.inc()
    with request_duration.time():
        response = await call_next(request)
    return response
```

### 2. Log Aggregation

```bash
# Install Loki + Promtail for log aggregation
helm repo add grafana https://grafana.github.io/helm-charts
helm install loki grafana/loki-stack \
  --namespace monitoring \
  --set promtail.enabled=true \
  --set grafana.enabled=true
```

### 3. Distributed Tracing

```bash
# Install Jaeger
kubectl create namespace observability
kubectl apply -f https://raw.githubusercontent.com/jaegertracing/jaeger-operator/main/deploy/crds/jaegertracing.io_jaegers_crd.yaml
kubectl apply -n observability -f https://raw.githubusercontent.com/jaegertracing/jaeger-operator/main/deploy/operator.yaml
```

## 🔒 Security Best Practices

1. **Secrets Management**

   ```bash
   # Use AWS Secrets Manager
   aws secretsmanager create-secret \
     --name mcp-servers/github-token \
     --secret-string "ghp_your_token"

   # Use Kubernetes External Secrets
   helm install external-secrets external-secrets/external-secrets \
     --namespace external-secrets \
     --create-namespace
   ```

2. **Network Policies**

   ```yaml
   # Restrict pod-to-pod communication
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: mcp-network-policy
   spec:
     podSelector:
       matchLabels:
         app: goal-agent-server
     policyTypes:
       - Ingress
       - Egress
     ingress:
       - from:
           - podSelector:
               matchLabels:
                 app: memory-cache-server
   ```

3. **Pod Security Standards**
   ```yaml
   # Enforce security context
   securityContext:
     runAsNonRoot: true
     runAsUser: 1000
     fsGroup: 1000
     capabilities:
       drop:
         - ALL
     readOnlyRootFilesystem: true
   ```

## 🧪 Testing the Deployment

```bash
# 1. Check all pods are running
kubectl get pods -n mcp-servers

# 2. Test each service health endpoint
for service in memory-cache goal-agent github jira internet; do
  URL=$(kubectl get svc ${service}-service -n mcp-servers -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
  curl -f http://${URL}:800X/health || echo "Failed: $service"
done

# 3. Test from Claude Desktop
# Update config and restart Claude Desktop
# Try: "Create a goal to test the cloud deployment"

# 4. Load test (optional)
kubectl run load-test --rm -i --restart=Never --image=williamyeh/wrk -- \
  wrk -t4 -c100 -d30s http://goal-agent-service:8002/health
```

## 📚 Maintenance Tasks

### Daily

- ✅ Check pod health: `kubectl get pods -n mcp-servers`
- ✅ Monitor error logs: `kubectl logs -f deployment/goal-agent-server -n mcp-servers`

### Weekly

- ✅ Review resource usage
- ✅ Check for security updates
- ✅ Review cost reports

### Monthly

- ✅ Update dependencies
- ✅ Rotate secrets
- ✅ Review and optimize resource allocations
- ✅ Test disaster recovery procedures

## 🆘 Troubleshooting

### Pods not starting

```bash
kubectl describe pod <pod-name> -n mcp-servers
kubectl logs <pod-name> -n mcp-servers
```

### Database connection issues

```bash
# Test from within cluster
kubectl run -it --rm debug --image=postgres:15 --restart=Never -- \
  psql -h postgres-service -U postgres -d mcp_goals
```

### High latency

```bash
# Check pod resources
kubectl top pods -n mcp-servers

# Scale up if needed
kubectl scale deployment/goal-agent-server --replicas=5 -n mcp-servers
```

## 🎓 Next Steps

1. **Set up custom domain**: Point DNS to LoadBalancers
2. **Enable monitoring**: Install Prometheus + Grafana
3. **Configure backup**: Automate database backups
4. **Implement CD**: Set up GitOps with ArgoCD
5. **Add caching layer**: Implement CloudFront/CloudFlare

## 📞 Support

- Documentation: `/cloud/` directory
- Issues: GitHub Issues
- Slack: #mcp-servers channel

---

**Congratulations!** 🎉 You now have a production-grade, cloud-native MCP deployment that Claude Desktop can connect to from anywhere!
