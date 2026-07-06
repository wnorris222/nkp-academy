# NKP Academy — common tasks.
# Override defaults on the CLI, e.g.:  make build IMAGE=ghcr.io/acme/nkp-academy TAG=1.2.3

IMAGE      ?= wnorris22/nkp
TAG        ?= 1.0.0
NAMESPACE  ?= nkp-academy
RELEASE    ?= nkp-academy
CHART      := deploy/helm/nkp-academy
PLATFORMS  ?= linux/amd64

BACKEND    := backend
PY         := $(BACKEND)/.venv/bin/python
PIP        := $(BACKEND)/.venv/bin/pip

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | sort | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

## ---- Local development ----

.PHONY: venv
venv: ## Create the backend virtualenv and install dev deps
	python3 -m venv $(BACKEND)/.venv
	$(PIP) install -q --upgrade pip
	$(PIP) install -q -e "$(BACKEND)[dev]"

.PHONY: dev-backend
dev-backend: ## Run the FastAPI backend with autoreload on :8000
	cd $(BACKEND) && .venv/bin/uvicorn app.main:app --reload --port 8000

.PHONY: dev-frontend
dev-frontend: ## Run the Vite dev server on :5173 (proxies /api to :8000)
	cd frontend && npm install && npm run dev

.PHONY: test
test: ## Run the backend test suite
	cd $(BACKEND) && .venv/bin/python -m pytest -q

.PHONY: lint
lint: ## Ruff-lint the backend
	cd $(BACKEND) && .venv/bin/ruff check app tests

## ---- Container ----

.PHONY: build
build: ## Build the container image
	docker build -t $(IMAGE):$(TAG) .

.PHONY: run
run: ## Run the built image locally on :8000
	docker run --rm -p 8000:8000 $(IMAGE):$(TAG)

.PHONY: compose-up
compose-up: ## Start the local stack via docker compose
	docker compose up --build

.PHONY: push
push: ## Push the image to the registry
	docker push $(IMAGE):$(TAG)

.PHONY: buildx-push
buildx-push: ## Build for target platforms and push (for NKP amd64 nodes)
	docker buildx build --platform $(PLATFORMS) -t $(IMAGE):$(TAG) --push .

## ---- Deploy to NKP / Kubernetes ----

.PHONY: helm-lint
helm-lint: ## Lint the Helm chart
	helm lint $(CHART)

.PHONY: helm-template
helm-template: ## Render the Helm chart to stdout
	helm template $(RELEASE) $(CHART) --namespace $(NAMESPACE)

.PHONY: deploy
deploy: ## Install/upgrade the release on the current kube-context (NKP cluster)
	helm upgrade --install $(RELEASE) $(CHART) \
	  --namespace $(NAMESPACE) --create-namespace \
	  --set image.repository=$(IMAGE) --set image.tag=$(TAG)

.PHONY: deploy-raw
deploy-raw: ## Apply the raw manifests instead of Helm
	kubectl apply -f deploy/k8s/

.PHONY: undeploy
undeploy: ## Uninstall the Helm release
	helm uninstall $(RELEASE) --namespace $(NAMESPACE)

.PHONY: clean
clean: ## Remove local build/venv artifacts
	rm -rf $(BACKEND)/.venv frontend/node_modules frontend/dist $(BACKEND)/*.db
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
