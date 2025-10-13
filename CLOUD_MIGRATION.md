# 🚀 Migrating from Local to Cloud

Complete guide to migrate your existing local MCP setup to the cloud.

## Overview

This guide helps you transition from running MCP servers locally to a production cloud deployment without downtime.

## Pre-Migration Checklist

- [ ] All local servers working correctly
- [ ] Cloud account ready (AWS/GCP/Azure)
- [ ] `kubectl`, `helm`, `terraform` installed
- [ ] Backup of existing data (PostgreSQL, Redis)
- [ ] API tokens and credentials ready

## Migration Strategy

### Option 1: Parallel Migration (Recommended)

Run both local and cloud in parallel, switch when ready.

**Pros:**

- Zero downtime
- Easy rollback
- Test thoroughly before switching

**Timeline:** 1-2 days

### Option 2: Direct Migration

Stop local, deploy cloud, migrate data.

**Pros:**

- Clean cutover
- No dual maintenance

**Cons:**

- Some downtime (1-2 hours)

**Timeline:** 4-6 hours

## Step-by-Step Migration

### Phase 1: Deploy Cloud Infrastructure (30 min)

```bash
# 1. Deploy infrastructure
cd cloud/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your settings
terraform init
terraform apply

# 2. Get connection info
export POSTGRES_HOST=$(terraform output -raw postgres_endpoint)
export REDIS_HOST=$(terraform output -raw redis_endpoint)
```

### Phase 2: Build and Deploy Services (20 min)

```bash
# 1. Build images
cd cloud/docker
./build-all.sh

# 2. Push to registry
export REGISTRY=your-registry.com
for server in memory-cache goal-agent github jira internet; do
  docker tag mcp-servers/${server}:latest ${REGISTRY}/mcp-servers/${server}:latest
  docker push ${REGISTRY}/mcp-servers/${server}:latest
done

# 3. Deploy with Helm
cd cloud/helm
cp secrets.yaml.example secrets.yaml
# Edit secrets.yaml
helm install mcp-servers ./mcp-servers -f secrets.yaml
```

### Phase 3: Migrate Data (30 min)

#### PostgreSQL Migration

```bash
# 1. Backup local database
pg_dump -h localhost -U postgres mcp_goals > mcp_goals_backup.sql

# 2. Restore to cloud
psql -h $POSTGRES_HOST -U postgres mcp_goals < mcp_goals_backup.sql

# 3. Verify data
psql -h $POSTGRES_HOST -U postgres mcp_goals -c "SELECT COUNT(*) FROM goals;"
```

#### Redis Migration (Optional)

```bash
# Redis is typically used for caching, so no migration needed
# Data will rebuild automatically as servers run

# If you need to migrate:
# 1. Backup
redis-cli --rdb /tmp/redis_backup.rdb

# 2. Restore
redis-cli -h $REDIS_HOST --pipe < /tmp/redis_backup.rdb
```

### Phase 4: Update Claude Desktop (10 min)

```bash
# 1. Copy proxy script
cp cloud/mcp-http-proxy.py ~/mcp-http-proxy.py
chmod +x ~/mcp-http-proxy.py

# 2. Get service URLs
kubectl get services -n mcp-servers

# 3. Update Claude Desktop config
# Backup existing config
cp ~/.config/Claude/claude_desktop_config.json \
   ~/.config/Claude/claude_desktop_config.json.backup

# Update with cloud URLs (see example below)
```

**Example Claude Desktop Config:**

```json
{
  "mcpServers": {
    "goal-agent": {
      "command": "python",
      "args": [
        "/home/yourusername/mcp-http-proxy.py",
        "http://a123456789.us-east-1.elb.amazonaws.com:8002"
      ],
      "env": {}
    },
    "github": {
      "command": "python",
      "args": [
        "/home/yourusername/mcp-http-proxy.py",
        "http://a123456789.us-east-1.elb.amazonaws.com:8003"
      ],
      "env": {}
    }
    // ... other servers
  }
}
```

### Phase 5: Test Cloud Deployment (15 min)

```bash
# 1. Check all pods running
kubectl get pods -n mcp-servers

# 2. Test health endpoints
for port in 8001 8002 8003 8004 8005; do
  URL=$(kubectl get svc -n mcp-servers -o jsonpath="{.items[*].status.loadBalancer.ingress[0].hostname}" | awk '{print $1}')
  curl -f http://${URL}:${port}/health || echo "Failed: port $port"
done

# 3. Test from Claude Desktop
# Restart Claude Desktop
# Try: "Create a goal to test cloud deployment"
# Try: "List my GitHub repositories"
```

### Phase 6: Monitor and Validate (1 day)

Run both systems in parallel for 24 hours:

```bash
# Monitor cloud deployment
kubectl top pods -n mcp-servers
kubectl logs -f deployment/goal-agent-server -n mcp-servers

# Compare results
# Local: curl http://localhost:8002/api/goals
# Cloud: curl http://$CLOUD_URL:8002/api/goals
```

### Phase 7: Decommission Local (When Ready)

```bash
# 1. Stop local servers
mcpctl stop

# 2. Backup local data one more time
pg_dump -h localhost -U postgres mcp_goals > final_backup.sql

# 3. Optional: Keep local for development
# Update ports to avoid conflicts
```

## Rollback Plan

If something goes wrong:

```bash
# 1. Restore Claude Desktop config
cp ~/.config/Claude/claude_desktop_config.json.backup \
   ~/.config/Claude/claude_desktop_config.json

# 2. Restart Claude Desktop

# 3. Your local setup is still running!
```

## Common Migration Issues

### Issue: Can't connect to cloud services

**Solution:**

```bash
# Check LoadBalancer provisioning
kubectl get services -n mcp-servers

# Check security groups (AWS)
aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$VPC_ID"

# Test from inside cluster
kubectl run test --rm -it --image=curlimages/curl -- \
  curl -f http://goal-agent-service:8002/health
```

### Issue: Database connection timeout

**Solution:**

```bash
# Check RDS security group allows connections from EKS
# Update security group to allow port 5432 from VPC CIDR

# Test connection
kubectl run psql --rm -it --image=postgres:15 -- \
  psql -h $POSTGRES_HOST -U postgres -d mcp_goals
```

### Issue: High latency from Claude Desktop

**Solution:**

```bash
# 1. Check proxy logs
tail -f /tmp/mcp-http-proxy.log

# 2. Use region closer to you
# 3. Enable caching (Redis)
# 4. Set up CloudFront/CDN
```

## Post-Migration Tasks

### 1. Set Up Custom Domain (Recommended)

```bash
# Install cert-manager
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true

# Update Helm values
helm upgrade mcp-servers ./mcp-servers \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=mcp.yourdomain.com
```

### 2. Enable Monitoring

```bash
# Install Prometheus + Grafana
make monitoring

# Access Grafana
make grafana
```

### 3. Set Up Automated Backups

```bash
# PostgreSQL backups (already enabled by Terraform)
# Point-in-time recovery available

# Set retention
aws rds modify-db-instance \
  --db-instance-identifier mcp-postgres \
  --backup-retention-period 30
```

### 4. Configure Auto-Scaling

```bash
# Update Helm values
helm upgrade mcp-servers ./mcp-servers \
  --set autoscaling.enabled=true \
  --set autoscaling.minReplicas=2 \
  --set autoscaling.maxReplicas=10
```

### 5. Enable CI/CD

The GitHub Actions workflow is already configured!

Just push to `main` branch and it deploys automatically.

## Cost Comparison

| Aspect       | Local            | Cloud       |
| ------------ | ---------------- | ----------- |
| Hardware     | Your computer    | None        |
| Electricity  | ~$20/month       | Included    |
| Services     | $0               | ~$450/month |
| Maintenance  | Your time        | Automated   |
| Availability | When computer on | 99.9%       |
| Scalability  | 1 machine        | Auto-scale  |
| **Total**    | ~$20/month       | ~$450/month |

**Is it worth it?**

- For personal projects: Maybe not
- For teams: Absolutely yes
- For production: Essential

## Migration Checklist

- [ ] Cloud infrastructure deployed
- [ ] Services running and healthy
- [ ] Database migrated and verified
- [ ] Claude Desktop updated and tested
- [ ] Monitoring enabled
- [ ] Backups configured
- [ ] Custom domain set up (optional)
- [ ] Team notified
- [ ] Documentation updated
- [ ] Local backup kept safe
- [ ] Ran in parallel for 24+ hours
- [ ] Ready to decommission local

## Need Help?

- **Documentation**: [CLOUD_DEPLOYMENT_GUIDE.md](cloud/CLOUD_DEPLOYMENT_GUIDE.md)
- **Quick Start**: [QUICK_START.md](cloud/QUICK_START.md)
- **Issues**: https://github.com/souravs72/claude-mcp-setup/issues
- **Email**: sourav@clapgrow.com

---

**Migration complete!** 🎉 Welcome to cloud-native MCP!
