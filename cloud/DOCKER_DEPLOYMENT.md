# 🐳 Docker-Based Cloud Deployment

Deploy without installing any tools locally! Everything runs in a container.

## 🎯 Why Docker-Based Deployment?

**Benefits:**

- ✅ No local tool installations required
- ✅ Consistent environment across all machines
- ✅ All dependencies included (kubectl, helm, terraform, AWS CLI)
- ✅ Works the same everywhere
- ✅ Easy to version control
- ✅ Perfect for CI/CD

## 🚀 Quick Start

### Option 1: Interactive Deployment Container

```bash
cd /home/clapgrow/Desktop/claude-mcp-setup/cloud

# Launch deployment container with all tools
./docker-deploy.sh
```

This gives you a shell with:

- ✅ kubectl
- ✅ helm
- ✅ terraform
- ✅ AWS CLI
- ✅ Docker CLI
- ✅ GitHub CLI

Then inside the container:

```bash
# Deploy everything
./deploy.sh production aws

# Or step by step:
terraform init
terraform apply
helm install mcp-servers ./helm/mcp-servers
```

### Option 2: One-Command Deployment

```bash
cd /home/clapgrow/Desktop/claude-mcp-setup/cloud

# Build and deploy in one command
docker run -it --rm \
  -v $(pwd)/..:/workspace \
  -v ~/.aws:/root/.aws:ro \
  -v ~/.kube:/root/.kube \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e AWS_REGION=ap-south-1 \
  --workdir /workspace/cloud \
  $(docker build -q -f Dockerfile.deployer .) \
  ./deploy.sh production aws
```

## 📦 What's in the Container?

The `mcp-deployer` container includes:

| Tool       | Version | Purpose                |
| ---------- | ------- | ---------------------- |
| AWS CLI    | Latest  | AWS operations         |
| kubectl    | Latest  | Kubernetes management  |
| Helm       | 3.x     | Package management     |
| Terraform  | Latest  | Infrastructure as Code |
| Docker CLI | Latest  | Build images           |
| GitHub CLI | Latest  | GitHub operations      |
| Git        | Latest  | Version control        |

## 🔧 Container Details

### Dockerfile: `Dockerfile.deployer`

Built on Ubuntu 22.04 with all cloud deployment tools pre-installed.

**Build the container:**

```bash
cd cloud
docker build -t mcp-deployer -f Dockerfile.deployer .
```

**Verify tools:**

```bash
docker run --rm mcp-deployer aws --version
docker run --rm mcp-deployer kubectl version --client
docker run --rm mcp-deployer helm version
docker run --rm mcp-deployer terraform version
```

## 🎮 Usage Examples

### Deploy Infrastructure

```bash
# Launch container
./docker-deploy.sh

# Inside container:
cd terraform
terraform init
terraform apply -auto-approve
```

### Build and Push Images

```bash
# Launch container
./docker-deploy.sh

# Inside container:
cd docker
./build-all.sh

# Tag and push to ECR
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export REGISTRY=${AWS_ACCOUNT_ID}.dkr.ecr.ap-south-1.amazonaws.com

aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin $REGISTRY

for server in memory-cache goal-agent github jira internet; do
  docker tag mcp-servers/${server}:latest ${REGISTRY}/mcp-servers/${server}:latest
  docker push ${REGISTRY}/mcp-servers/${server}:latest
done
```

### Deploy with Helm

```bash
# Launch container
./docker-deploy.sh

# Inside container:
helm install mcp-servers ./helm/mcp-servers \
  --namespace mcp-servers \
  --create-namespace \
  -f secrets.yaml
```

### Check Deployment

```bash
# Launch container
./docker-deploy.sh

# Inside container:
kubectl get pods -n mcp-servers
kubectl get services -n mcp-servers
kubectl logs -f deployment/goal-agent-server -n mcp-servers
```

## 🔐 Credentials Mounting

The container mounts your local credentials:

```bash
-v ~/.aws:/root/.aws:ro           # AWS credentials (read-only)
-v ~/.kube:/root/.kube             # Kubernetes config
-v /var/run/docker.sock:/var/run/docker.sock  # Docker daemon
```

**Security Notes:**

- AWS credentials are mounted read-only
- Docker socket allows building images
- All credentials stay on your machine

## 🌟 Advanced Usage

### Custom Environment Variables

```bash
docker run -it --rm \
  -v $(pwd)/..:/workspace \
  -v ~/.aws:/root/.aws:ro \
  -e AWS_REGION=ap-south-1 \
  -e AWS_PROFILE=production \
  -e KUBECONFIG=/root/.kube/config \
  --workdir /workspace/cloud \
  mcp-deployer \
  bash
```

### Run Specific Commands

```bash
# Just run terraform
docker run --rm \
  -v $(pwd)/..:/workspace \
  -v ~/.aws:/root/.aws:ro \
  --workdir /workspace/cloud/terraform \
  mcp-deployer \
  terraform plan

# Just check cluster
docker run --rm \
  -v ~/.kube:/root/.kube \
  mcp-deployer \
  kubectl get nodes
```

### Build Images Inside Container

```bash
docker run -it --rm \
  -v $(pwd)/..:/workspace \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --workdir /workspace/cloud/docker \
  mcp-deployer \
  ./build-all.sh
```

## 🚀 CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/docker-deploy.yml
name: Deploy with Docker

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-south-1

      - name: Deploy with container
        run: |
          cd cloud
          docker build -t mcp-deployer -f Dockerfile.deployer .
          docker run --rm \
            -v $(pwd)/..:/workspace \
            -v ~/.aws:/root/.aws:ro \
            --workdir /workspace/cloud \
            mcp-deployer \
            ./deploy.sh production aws
```

### GitLab CI

```yaml
# .gitlab-ci.yml
deploy:
  image: docker:latest
  services:
    - docker:dind
  script:
    - cd cloud
    - docker build -t mcp-deployer -f Dockerfile.deployer .
    - docker run --rm
      -v $(pwd)/..:/workspace
      -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID
      -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY
      --workdir /workspace/cloud
      mcp-deployer
      ./deploy.sh production aws
```

## 📊 Container Image Details

**Image Size:** ~500MB (all tools included)

**Build Time:** ~5 minutes (first time only)

**Base Image:** Ubuntu 22.04 LTS

## 🔄 Updating the Container

```bash
# Rebuild with latest tools
cd cloud
docker build --no-cache -t mcp-deployer -f Dockerfile.deployer .

# Or pull updates
docker pull ubuntu:22.04
docker build -t mcp-deployer -f Dockerfile.deployer .
```

## 🐛 Troubleshooting

### Container won't start

```bash
# Check Docker is running
docker info

# Check permissions
sudo usermod -aG docker $USER
newgrp docker
```

### Can't connect to AWS

```bash
# Verify credentials are mounted
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  mcp-deployer \
  aws sts get-caller-identity
```

### Can't build images

```bash
# Check Docker socket is mounted
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  mcp-deployer \
  docker ps
```

## 💡 Tips & Tricks

### Use Docker Compose

```yaml
# docker-compose.yml
version: "3.8"
services:
  deployer:
    build:
      context: .
      dockerfile: Dockerfile.deployer
    volumes:
      - ..:/workspace
      - ~/.aws:/root/.aws:ro
      - ~/.kube:/root/.kube
      - /var/run/docker.sock:/var/run/docker.sock
    working_dir: /workspace/cloud
    environment:
      - AWS_REGION=ap-south-1
    stdin_open: true
    tty: true
```

Run:

```bash
docker-compose run deployer ./deploy.sh production aws
```

### Create Deployment Alias

```bash
# Add to ~/.bashrc
alias mcp-deploy='docker run -it --rm \
  -v $(pwd):/workspace \
  -v ~/.aws:/root/.aws:ro \
  -v ~/.kube:/root/.kube \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --workdir /workspace/cloud \
  mcp-deployer'

# Usage:
mcp-deploy ./deploy.sh production aws
```

## ✅ Comparison: Local vs Docker

| Aspect                | Local Install    | Docker Container |
| --------------------- | ---------------- | ---------------- |
| **Setup Time**        | 30 minutes       | 5 minutes        |
| **Dependencies**      | Manual install   | All included     |
| **Version Conflicts** | Possible         | None             |
| **Consistency**       | Varies           | Identical        |
| **CI/CD Ready**       | No               | Yes              |
| **Portability**       | Machine-specific | Works anywhere   |

## 🎉 Summary

**Docker deployment is perfect for:**

- ✅ Clean deployments without local tool pollution
- ✅ CI/CD pipelines
- ✅ Team consistency
- ✅ Quick onboarding
- ✅ Testing in isolated environments

**Just run:**

```bash
cd /home/clapgrow/Desktop/claude-mcp-setup/cloud
./docker-deploy.sh
```

And you're in a fully-equipped deployment environment! 🚀
