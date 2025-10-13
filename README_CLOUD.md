# ☁️ Cloud-Native MCP Servers

**Production-ready MCP servers that connect to Claude from anywhere**

## 🎯 What This Is

This directory contains everything you need to deploy your MCP servers to the cloud with enterprise-grade reliability:

- **Kubernetes deployments** for all services
- **Terraform** for automated infrastructure
- **Helm charts** for easy deployment
- **CI/CD pipelines** with GitHub Actions
- **Production-grade Dockerfiles** with security best practices
- **HTTP proxy** for Claude Desktop connectivity

## 🚀 Quick Start

```bash
# Deploy everything in 30 minutes
cd cloud
./deploy.sh production aws
```

See [QUICK_START.md](cloud/QUICK_START.md) for step-by-step instructions.

## 📁 What's Inside

```
cloud/
├── QUICK_START.md              # 30-minute deployment guide
├── CLOUD_DEPLOYMENT_GUIDE.md   # Comprehensive production guide
├── deploy.sh                   # Automated deployment script
├── mcp-http-proxy.py          # Proxy for Claude Desktop
│
├── kubernetes/                 # Raw Kubernetes manifests
│   ├── namespace.yaml
│   ├── postgres-deployment.yaml
│   ├── redis-deployment.yaml
│   └── mcp-servers-deployment.yaml
│
├── helm/                       # Helm charts (recommended)
│   └── mcp-servers/
│       ├── Chart.yaml
│       ├── values.yaml        # Customize your deployment
│       └── templates/
│
├── terraform/                  # Infrastructure as Code
│   └── main.tf                # EKS, RDS, ElastiCache, VPC
│
├── docker/                     # Production Dockerfiles
│   ├── Dockerfile.base
│   ├── Dockerfile.memory-cache
│   ├── Dockerfile.goal-agent
│   └── build-all.sh           # Build all images
│
└── config-examples/            # Claude Desktop configs
    ├── claude-desktop-cloud.json
    └── claude-desktop-loadbalancer.json
```

## 🏗️ Architecture

```
Claude Desktop (Your Computer)
      ↓ stdio → HTTP
   MCP Proxy (local)
      ↓ HTTPS
   Load Balancer (cloud)
      ↓
   ┌────────────┬────────────┬──────────┐
   │   Memory   │    Goal    │  GitHub  │
   │   Cache    │   Agent    │  Server  │
   └─────┬──────┴──────┬─────┴──────────┘
         │             │
    ┌────┴──┐     ┌────┴────┐
    │ Redis │     │Postgres │
    └───────┘     └─────────┘
```

## 💡 Why Cloud-Native?

### Local Setup (Current)

- ❌ Only works on your machine
- ❌ Manual Redis/PostgreSQL management
- ❌ No high availability
- ❌ No auto-scaling
- ❌ No monitoring

### Cloud Setup (This)

- ✅ Works from anywhere
- ✅ Managed databases (RDS/ElastiCache)
- ✅ High availability (multi-AZ)
- ✅ Auto-scaling (2-10 pods)
- ✅ Production monitoring
- ✅ CI/CD automation
- ✅ Professional setup

## 📊 Features

| Feature              | Local              | Cloud                |
| -------------------- | ------------------ | -------------------- |
| **Availability**     | Single machine     | 99.9% uptime         |
| **Scalability**      | 1 instance         | 2-10+ instances      |
| **Data Persistence** | Local disk         | Managed databases    |
| **Monitoring**       | Manual logs        | Prometheus + Grafana |
| **Updates**          | Manual             | Automated CI/CD      |
| **Cost**             | $0 (your hardware) | ~$450/month          |
| **Setup Time**       | 10 min             | 30 min               |

## 🎯 Deployment Options

### 1. AWS (Recommended)

- **EKS** for Kubernetes
- **RDS PostgreSQL** for data
- **ElastiCache Redis** for caching
- **Cost**: ~$450/month
- **Setup**: [QUICK_START.md](cloud/QUICK_START.md)

### 2. Google Cloud Platform

- **GKE** for Kubernetes
- **Cloud SQL** for PostgreSQL
- **Memorystore** for Redis
- **Cost**: ~$400/month
- **Setup**: Adapt terraform/main.tf

### 3. Azure

- **AKS** for Kubernetes
- **Azure Database** for PostgreSQL
- **Azure Cache** for Redis
- **Cost**: ~$420/month
- **Setup**: Adapt terraform/main.tf

### 4. Kubernetes (Any Provider)

If you already have a Kubernetes cluster:

```bash
cd cloud/helm
helm install mcp-servers ./mcp-servers
```

## 🔧 Configuration

### Minimal (Use Defaults)

```bash
# Just set your secrets
cd cloud/helm
cat > secrets.yaml <<EOF
secrets:
  githubToken: "ghp_your_token"
  jiraApiToken: "your_jira_token"
EOF

helm install mcp-servers ./mcp-servers -f secrets.yaml
```

### Advanced (Customize Everything)

Edit `cloud/helm/mcp-servers/values.yaml`:

- Replica counts
- Resource limits
- Autoscaling rules
- Storage sizes
- Custom domains

## 🚦 Quick Commands

```bash
# Deploy everything
cd cloud && ./deploy.sh production aws

# Check status
kubectl get pods -n mcp-servers

# View logs
kubectl logs -f deployment/goal-agent-server -n mcp-servers

# Scale up
kubectl scale deployment/goal-agent-server --replicas=5 -n mcp-servers

# Update configuration
helm upgrade mcp-servers ./mcp-servers -f new-values.yaml

# Rollback
helm rollback mcp-servers

# Destroy everything
terraform destroy
helm uninstall mcp-servers
```

## 💰 Cost Breakdown

### Production (~$450/month)

- EKS cluster: $73
- EC2 (3x t3.medium): $90
- RDS PostgreSQL: $60
- ElastiCache Redis: $15
- LoadBalancers (5): $125
- Data transfer: $90

### Development (~$150/month)

- Smaller instances (t3.small)
- Single AZ
- Minimal redundancy

**Cost optimization:**

- Use Reserved Instances (save 30-70%)
- Use Spot Instances for dev
- Auto-scale down during off-hours

## 🔒 Security

- ✅ Non-root containers
- ✅ Network policies
- ✅ Secrets management
- ✅ TLS/HTTPS everywhere
- ✅ Role-based access control (RBAC)
- ✅ Regular security updates

## 📈 Monitoring

```bash
# Install Prometheus + Grafana
helm install prometheus prometheus-community/kube-prometheus-stack

# Access Grafana
kubectl port-forward svc/prometheus-grafana 3000:80 -n monitoring
# Open http://localhost:3000
```

Pre-built dashboards for:

- Server health
- Request rates
- Error rates
- Resource usage
- Database metrics

## 🧪 Testing

```bash
# Run smoke tests
kubectl run test --rm -i --restart=Never \
  --image=curlimages/curl -- \
  curl -f http://goal-agent-service:8002/health

# Load testing
kubectl run load-test --rm -i --restart=Never \
  --image=williamyeh/wrk -- \
  wrk -t4 -c100 -d30s http://goal-agent-service:8002/api/goals
```

## 📚 Documentation

- **[QUICK_START.md](cloud/QUICK_START.md)** - Get running in 30 minutes
- **[CLOUD_DEPLOYMENT_GUIDE.md](cloud/CLOUD_DEPLOYMENT_GUIDE.md)** - Complete production guide
- **[terraform/README.md](cloud/terraform/README.md)** - Infrastructure details
- **[helm/mcp-servers/README.md](cloud/helm/mcp-servers/README.md)** - Helm chart reference

## 🆘 Troubleshooting

### Pods not starting

```bash
kubectl describe pod <pod-name> -n mcp-servers
kubectl logs <pod-name> -n mcp-servers
```

### Can't connect from Claude

1. Check LoadBalancer URLs: `kubectl get services -n mcp-servers`
2. Test endpoint: `curl http://YOUR_URL:8002/health`
3. Check proxy logs: `tail -f /tmp/mcp-http-proxy.log`

### High costs

1. Review resource usage: `kubectl top pods -n mcp-servers`
2. Scale down: `kubectl scale deployment/X --replicas=1`
3. Use Spot Instances for non-critical workloads

## 🎓 Next Steps

1. ✅ Deploy to cloud
2. ⬜ Set up custom domain
3. ⬜ Enable HTTPS with cert-manager
4. ⬜ Configure monitoring
5. ⬜ Set up automated backups
6. ⬜ Implement auto-scaling
7. ⬜ Add CD with ArgoCD

## 🤝 Contributing

Improvements welcome! Areas to contribute:

- Additional cloud providers (Azure, DigitalOcean)
- Cost optimization strategies
- Monitoring dashboards
- Security enhancements
- Documentation

## 📞 Support

- **Documentation**: See `/cloud/` directory
- **Issues**: https://github.com/souravs72/claude-mcp-setup/issues
- **Community**: Discord/Slack
- **Email**: sourav@clapgrow.com

---

**Ready to go cloud-native?** 🚀

Start here: [QUICK_START.md](cloud/QUICK_START.md)
