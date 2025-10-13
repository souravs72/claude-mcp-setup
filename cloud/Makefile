# Makefile for Cloud Deployment

.PHONY: help deploy build push install test clean

# Variables
ENVIRONMENT ?= production
CLOUD_PROVIDER ?= aws
NAMESPACE ?= mcp-servers

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

deploy: ## Full deployment (infrastructure + images + kubernetes)
	@echo "Deploying to $(CLOUD_PROVIDER) ($(ENVIRONMENT))..."
	./deploy.sh $(ENVIRONMENT) $(CLOUD_PROVIDER)

infra: ## Deploy infrastructure with Terraform
	@echo "Deploying infrastructure..."
	cd terraform && terraform init && terraform apply

build: ## Build Docker images
	@echo "Building Docker images..."
	cd docker && ./build-all.sh

push: ## Push images to registry
	@echo "Pushing images to registry..."
	@echo "Make sure you're logged in to your registry first!"
	# Add your push commands here

install: ## Install with Helm
	@echo "Installing with Helm..."
	cd helm && helm upgrade --install mcp-servers ./mcp-servers \
		--namespace $(NAMESPACE) \
		--create-namespace \
		-f secrets.yaml \
		--wait

uninstall: ## Uninstall Helm release
	@echo "Uninstalling..."
	helm uninstall mcp-servers -n $(NAMESPACE)

test: ## Run deployment tests
	@echo "Testing deployment..."
	kubectl get pods -n $(NAMESPACE)
	kubectl get services -n $(NAMESPACE)

status: ## Check deployment status
	@echo "Checking status..."
	@echo "\n=== Pods ==="
	kubectl get pods -n $(NAMESPACE)
	@echo "\n=== Services ==="
	kubectl get services -n $(NAMESPACE)
	@echo "\n=== Deployments ==="
	kubectl get deployments -n $(NAMESPACE)

logs: ## View logs (specify SERVICE=name)
	@if [ -z "$(SERVICE)" ]; then \
		echo "Usage: make logs SERVICE=goal-agent"; \
	else \
		kubectl logs -f deployment/$(SERVICE)-server -n $(NAMESPACE); \
	fi

scale: ## Scale deployment (specify SERVICE=name REPLICAS=n)
	@if [ -z "$(SERVICE)" ] || [ -z "$(REPLICAS)" ]; then \
		echo "Usage: make scale SERVICE=goal-agent REPLICAS=5"; \
	else \
		kubectl scale deployment/$(SERVICE)-server --replicas=$(REPLICAS) -n $(NAMESPACE); \
	fi

clean: ## Clean up resources
	@echo "Cleaning up..."
	helm uninstall mcp-servers -n $(NAMESPACE) || true
	kubectl delete namespace $(NAMESPACE) || true

destroy: ## Destroy all infrastructure (Terraform)
	@echo "WARNING: This will destroy all infrastructure!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cd terraform && terraform destroy; \
	fi

# Monitoring
monitoring: ## Install Prometheus + Grafana
	@echo "Installing monitoring stack..."
	helm repo add prometheus-community https://prometheus-community.github.io/helm-charts || true
	helm repo update
	helm install prometheus prometheus-community/kube-prometheus-stack \
		--namespace monitoring \
		--create-namespace

grafana: ## Port-forward Grafana
	@echo "Grafana will be available at http://localhost:3000"
	@echo "Default credentials: admin / prom-operator"
	kubectl port-forward svc/prometheus-grafana 3000:80 -n monitoring

# Utilities
urls: ## Get service URLs
	@echo "Service URLs:"
	@kubectl get services -n $(NAMESPACE) -o wide

proxy: ## Run local HTTP proxy for testing
	@echo "Starting MCP HTTP proxy..."
	@read -p "Enter service URL: " url; \
	python mcp-http-proxy.py $$url

version: ## Show version info
	@echo "Versions:"
	@echo "  kubectl: $$(kubectl version --client --short 2>/dev/null || echo 'not installed')"
	@echo "  helm: $$(helm version --short 2>/dev/null || echo 'not installed')"
	@echo "  terraform: $$(terraform version -json 2>/dev/null | jq -r '.terraform_version' || echo 'not installed')"
	@echo "  docker: $$(docker --version 2>/dev/null || echo 'not installed')"

