# DNS Configuration for frappewizard.com

After deploying your MCP servers to the cloud, you'll need to point your domain to the LoadBalancers.

## Step 1: Get LoadBalancer URLs

After deployment, get your LoadBalancer URLs:

```bash
kubectl get services -n mcp-servers -o wide
```

Example output:

```
NAME                    TYPE           EXTERNAL-IP
memory-cache-service    LoadBalancer   a123456789abcdef-1234567890.us-east-1.elb.amazonaws.com
goal-agent-service      LoadBalancer   a987654321fedcba-0987654321.us-east-1.elb.amazonaws.com
github-service          LoadBalancer   a111222333444555-1112223334.us-east-1.elb.amazonaws.com
jira-service            LoadBalancer   a666777888999000-6667778889.us-east-1.elb.amazonaws.com
internet-service        LoadBalancer   a555444333222111-5554443332.us-east-1.elb.amazonaws.com
```

## Step 2: Configure DNS Records

Go to your DNS provider (where you registered frappewizard.com) and add these CNAME records:

### Option 1: Individual Subdomains (Recommended)

```
Type    Name             Value                                          TTL
CNAME   memory-cache     a123456789abcdef-1234567890.us-east-1.elb...  300
CNAME   goal-agent       a987654321fedcba-0987654321.us-east-1.elb...  300
CNAME   github-service   a111222333444555-1112223334.us-east-1.elb...  300
CNAME   jira-service     a666777888999000-6667778889.us-east-1.elb...  300
CNAME   internet-service a555444333222111-5554443332.us-east-1.elb...  300
```

This creates:

- `memory-cache.frappewizard.com`
- `goal-agent.frappewizard.com`
- `github-service.frappewizard.com`
- `jira-service.frappewizard.com`
- `internet-service.frappewizard.com`

### Option 2: Single Subdomain with Ingress

If you enable ingress in Helm, you only need one DNS record:

```
Type    Name    Value                                          TTL
CNAME   mcp     your-ingress-loadbalancer.us-east-1.elb...    300
```

This creates: `mcp.frappewizard.com`

Then update your Helm values:

```yaml
ingress:
  enabled: true
  hosts:
    - host: mcp.frappewizard.com
      paths:
        - path: /memory-cache
          service: memory-cache-service
          port: 8001
        - path: /goal-agent
          service: goal-agent-service
          port: 8002
        # ... etc
```

## Step 3: Enable HTTPS with Let's Encrypt

### Install cert-manager

```bash
# Add Jetstack Helm repository
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Install cert-manager
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true
```

### Create ClusterIssuer

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

### Enable HTTPS in Helm

Update your Helm values:

```yaml
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    kubernetes.io/tls-acme: "true"
  hosts:
    - host: mcp.frappewizard.com
  tls:
    - secretName: mcp-tls
      hosts:
        - mcp.frappewizard.com
```

Upgrade deployment:

```bash
helm upgrade mcp-servers ./cloud/helm/mcp-servers -f secrets.yaml
```

## Step 4: Verify DNS

Wait 5-10 minutes for DNS propagation, then test:

```bash
# Check DNS resolution
nslookup memory-cache.frappewizard.com
nslookup goal-agent.frappewizard.com

# Test HTTPS (once cert-manager is set up)
curl https://goal-agent.frappewizard.com/health
```

## Step 5: Update Claude Desktop Config

Once DNS is working, update your Claude Desktop configuration:

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
    }
  }
}
```

**Restart Claude Desktop** and test!

## Troubleshooting

### DNS not resolving

```bash
# Check if DNS has propagated
dig memory-cache.frappewizard.com

# Clear local DNS cache (Linux)
sudo systemd-resolve --flush-caches

# Clear local DNS cache (macOS)
sudo dscacheutil -flushcache
```

### Certificate not issued

```bash
# Check certificate status
kubectl get certificate -n mcp-servers

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Describe certificate for details
kubectl describe certificate mcp-tls -n mcp-servers
```

### Connection refused

```bash
# Check if LoadBalancers are ready
kubectl get svc -n mcp-servers

# Test direct LoadBalancer connection
curl http://YOUR_LOADBALANCER_URL:8002/health
```

## Alternative: Using CloudFlare

If you use CloudFlare for DNS:

1. Add CNAME records (same as above)
2. Set SSL/TLS mode to "Full" (not "Flexible")
3. Enable "Always Use HTTPS"
4. Optional: Enable "HTTP/2" and "HTTP/3"

## Cost Considerations

- **DNS**: Usually free with domain registration
- **LoadBalancers**: ~$25/month per LoadBalancer
- **SSL Certificates**: Free with Let's Encrypt
- **Ingress**: Saves cost by using 1 LoadBalancer instead of 5

**Recommendation**: Use Ingress with a single LoadBalancer to save ~$100/month!

---

**Next Steps:**

1. Set up DNS records
2. Enable HTTPS with cert-manager
3. Update Claude Desktop config
4. Test end-to-end!
