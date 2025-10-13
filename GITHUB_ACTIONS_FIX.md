# 🔧 GitHub Actions Fix

## ❌ Problem

The GitHub Actions workflows are failing because:

1. **Wrong AWS Region** - Configured for `us-east-1` but your AWS is in `ap-south-1` (Mumbai)
2. **Infrastructure Doesn't Exist** - Trying to deploy to non-existent EKS clusters
3. **Workflow Order** - Deployment runs before infrastructure is created

## ✅ Solutions Applied

### Fix 1: Updated AWS Region

Changed all workflows from `us-east-1` → `ap-south-1` (Mumbai)

### Fix 2: Added Infrastructure Checks

Workflows now check if EKS cluster exists before trying to deploy:

```yaml
- name: Check if EKS cluster exists
  id: check-cluster
  run: |
    if aws eks describe-cluster --name mcp-servers-production --region ap-south-1 2>/dev/null; then
      echo "exists=true" >> $GITHUB_OUTPUT
    else
      echo "exists=false" >> $GITHUB_OUTPUT
      echo "⚠️  EKS cluster doesn't exist yet. Run Terraform first!"
    fi

- name: Deploy with Helm
  if: steps.check-cluster.outputs.exists == 'true'
  run: |
    helm upgrade --install mcp-servers ./cloud/helm/mcp-servers
```

### Fix 3: Build-Only Workflow

Created `.github/workflows/build-only.yml` that:
- ✅ Only builds Docker images
- ✅ Runs tests
- ✅ Doesn't try to deploy
- ✅ Perfect for when infrastructure isn't ready yet

## 🚀 Proper Deployment Order

### Phase 1: Build Images (GitHub Actions - Auto)

Just push to GitHub - images build automatically!

```bash
git push origin dev
```

✅ Builds all 5 Docker images  
✅ Runs tests  
✅ Pushes to GitHub Container Registry (ghcr.io)

### Phase 2: Deploy Infrastructure (Manual - One Time)

```bash
# Option A: Using Terraform locally
cd cloud/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your config
terraform init
terraform apply

# Option B: Using Docker container
cd cloud
./docker-deploy.sh
# Inside: cd terraform && terraform init && terraform apply
```

This creates:
- EKS cluster
- RDS PostgreSQL
- ElastiCache Redis
- VPC & networking

**Time:** ~15 minutes

### Phase 3: Enable Full Deployment (Auto)

Once infrastructure exists, rename workflow:

```bash
# Disable build-only, enable full deployment
mv .github/workflows/build-only.yml .github/workflows/build-only.yml.disabled
# The deploy.yml will now work because infrastructure exists!

git add .
git commit -m "Enable full deployment workflow"
git push origin main
```

Now every push to `main` will:
- ✅ Build images
- ✅ Run tests
- ✅ Deploy to Kubernetes
- ✅ Verify deployment

## 🎯 Quick Fix for Current Failing Workflows

The workflows are failing because they're trying to deploy but infrastructure doesn't exist yet.

**Solution:** Just use the build-only workflow for now!

### Step 1: Disable Full Deployment Temporarily

```bash
cd .github/workflows
mv deploy.yml deploy.yml.disabled
git add .
git commit -m "Use build-only workflow until infrastructure is ready"
git push origin dev
```

### Step 2: Deploy Infrastructure with Terraform

```bash
cd cloud/terraform

# Create config
cat > terraform.tfvars <<EOF
aws_region = "ap-south-1"
cluster_name = "mcp-servers-prod"
environment = "production"
github_token = "{{ from GitHub secrets }}"
jira_api_token = "{{ from GitHub secrets }}"
google_api_key = "{{ from GitHub secrets }}"
google_search_engine_id = "{{ from GitHub secrets }}"
EOF

# Deploy
terraform init
terraform apply
```

### Step 3: Re-enable Full Deployment

```bash
cd .github/workflows
mv deploy.yml.disabled deploy.yml
git add .
git commit -m "Enable full deployment - infrastructure ready"
git push origin main
```

## 🌟 Alternative: Simpler Approach

**Use the build-only workflow permanently!**

It's actually better to:
1. ✅ Let GitHub Actions build images
2. ✅ Deploy infrastructure manually with Terraform (one-time setup)
3. ✅ Deploy services manually with Helm (when needed)

This gives you more control and avoids dependency on GitHub Actions for infrastructure.

## 📋 Recommended Workflow

```bash
# 1. Push code (builds images automatically)
git push origin dev

# 2. Set GitHub secrets (one time)
cd cloud
./setup-github-secrets.sh

# 3. Deploy infrastructure (one time)
./deploy.sh production aws
# Or use Terraform directly

# 4. Update services (anytime)
helm upgrade mcp-servers ./helm/mcp-servers

# 5. Verify
kubectl get pods -n mcp-servers
```

## 🔍 Current Status

Based on https://github.com/souravs72/claude-mcp-setup/actions:

- ✅ Workflow runs are triggered (that's good!)
- ⚠️  They're failing because infrastructure doesn't exist yet (expected!)
- ✅ Docker builds are working
- ✅ Code is being validated

**This is normal for initial setup!**

## ✅ Fixed Files

1. ✅ `.github/workflows/deploy.yml` - Updated region, added checks
2. ✅ `.github/workflows/build-only.yml` - New safer workflow
3. ✅ Both workflows now handle missing infrastructure gracefully

## 🎯 What To Do Now

### Option 1: Use Build-Only Workflow (Recommended)

```bash
# Switch to build-only workflow
mv .github/workflows/deploy.yml .github/workflows/deploy.yml.later
git add .
git commit -m "Use build-only workflow for now"
git push origin dev

# Deploy infrastructure manually
cd cloud
./deploy.sh production aws
```

### Option 2: Deploy Infrastructure First

```bash
# Deploy infrastructure first
cd cloud/terraform
terraform init
terraform apply

# Then the deploy.yml workflow will work!
git push origin main
```

---

## 📞 Summary

**The workflows aren't "wrong" - they just can't deploy without infrastructure!**

**Solution:**
1. Use `build-only.yml` workflow (builds images only)
2. Deploy infrastructure manually with Terraform
3. Then optionally enable full deployment workflow

Or just manually deploy everything - you have full control!

See: [cloud/SETUP_INSTRUCTIONS.md](../cloud/SETUP_INSTRUCTIONS.md)

