.PHONY: help dev run start-all stop-all status api frontend database worker worker-start worker-stop worker-restart
.PHONY: test frontend-test-bib check lint ruff clean-cache export-docs
.PHONY: docker-dev docker-full docker-buildx-prepare docker-buildx-clean docker-buildx-reset
.PHONY: docker-push docker-push-latest docker-release docker-build-local tag

# Get version from pyproject.toml
VERSION := $(shell grep -m1 version pyproject.toml | cut -d'"' -f2)

# Image names for both registries
DOCKERHUB_IMAGE := lfnovo/open_notebook
GHCR_IMAGE := ghcr.io/lfnovo/open-notebook

# Build platforms
PLATFORMS := linux/amd64,linux/arm64

WORKER_MAX_TASKS ?= $(or $(SURREAL_COMMANDS_MAX_TASKS),5)

help:
	@echo "Lumina development commands"
	@echo ""
	@echo "Local development:"
	@echo "  make dev / make start-all   Start local dev environment via ./dev-init.sh"
	@echo "  make stop-all               Stop local dev environment via ./dev-init.sh stop"
	@echo "  make status                 Show local ports, PID file, and Docker DB status"
	@echo "  make api                    Start API only"
	@echo "  make frontend               Start frontend only"
	@echo "  make worker                 Start worker only with bounded concurrency"
	@echo "  make database               Start SurrealDB v3 from docker-compose.yml"
	@echo ""
	@echo "Checks:"
	@echo "  make test                   Run pytest tests/"
	@echo "  make ruff                   Run ruff --fix"
	@echo "  make lint                   Run mypy"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-dev             Build/run examples/docker-compose-dev.yml"
	@echo "  make docker-full            Build/run examples/docker-compose-full-local.yml"
	@echo "  make docker-build-local     Build local production image"

dev: start-all

run: start-all

start-all:
	@echo "🚀 Starting Lumina local development environment..."
	./dev-init.sh

stop-all:
	@echo "🛑 Stopping Lumina local development environment..."
	./dev-init.sh stop
	@docker compose down >/dev/null 2>&1 || true
	@echo "✅ Stop requested"

status:
	@echo "📊 Lumina local status"
	@printf "Dev PID file: "
	@if [ -f /tmp/lumina-dev.pid ] && kill -0 "$$(cat /tmp/lumina-dev.pid)" >/dev/null 2>&1; then \
		echo "✅ running ($$(cat /tmp/lumina-dev.pid))"; \
	elif [ -f /tmp/lumina-dev.pid ]; then \
		echo "⚠️ stale ($$(cat /tmp/lumina-dev.pid))"; \
	else \
		echo "❌ missing"; \
	fi
	@printf "SurrealDB 8000: "
	@lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1 && echo "✅ listening" || echo "❌ not listening"
	@printf "API 5055:      "
	@curl -fsS http://127.0.0.1:5055/api/auth/status >/dev/null 2>&1 && echo "✅ healthy" || echo "❌ not healthy"
	@printf "Frontend 3000: "
	@curl -fsS -I http://127.0.0.1:3000 >/dev/null 2>&1 && echo "✅ healthy" || echo "❌ not healthy"
	@printf "Worker:        "
	@pgrep -f "worker_with_timeout.py" >/dev/null 2>&1 && echo "✅ running" || echo "❌ not running"
	@echo ""
	@echo "Docker compose database:"
	@docker compose ps surrealdb 2>/dev/null || echo "  not running via docker compose"

database:
	docker compose up -d surrealdb

api:
	API_PORT="$${API_PORT:-5055}" uv run --env-file .env run_api.py

frontend:
	cd frontend && npm run dev -- --port "$${FRONTEND_PORT:-3000}"

worker: worker-start

worker-start:
	@echo "Starting surreal-commands worker with max tasks=$(WORKER_MAX_TASKS)..."
	uv run --env-file .env python3 scripts/worker_with_timeout.py --import-modules commands --max-tasks "$(WORKER_MAX_TASKS)"

worker-stop:
	@echo "Stopping local worker..."
	@pkill -f "worker_with_timeout.py" || true
	@pkill -f "surreal-commands-worker" || true

worker-restart: worker-stop
	@sleep 2
	@$(MAKE) worker-start

test:
	uv run pytest tests/

frontend-test-bib:
	cd frontend && npm run test -- --run src/lib/utils/source-references.bibliography.test.ts

check: ruff lint test

lint:
	uv run python -m mypy .

ruff:
	uv run ruff check . --fix

docker-dev:
	docker compose --project-directory . -f examples/docker-compose-dev.yml up --build

docker-full:
	docker compose --project-directory . -f examples/docker-compose-full-local.yml up --build

# === Docker Build Setup ===
docker-buildx-prepare:
	@docker buildx inspect multi-platform-builder >/dev/null 2>&1 || \
		docker buildx create --use --name multi-platform-builder --driver docker-container
	@docker buildx use multi-platform-builder

docker-buildx-clean:
	@echo "🧹 Cleaning up buildx builders..."
	@docker buildx rm multi-platform-builder 2>/dev/null || true
	@docker ps -a | grep buildx_buildkit | awk '{print $$1}' | xargs -r docker rm -f 2>/dev/null || true
	@echo "✅ Buildx cleanup complete!"

docker-buildx-reset: docker-buildx-clean docker-buildx-prepare
	@echo "✅ Buildx reset complete!"

# === Docker Build Targets ===

docker-build-local:
	@echo "🔨 Building production image locally ($(shell uname -m))..."
	docker build \
		-t $(DOCKERHUB_IMAGE):$(VERSION) \
		-t $(DOCKERHUB_IMAGE):local \
		.
	@echo "✅ Built $(DOCKERHUB_IMAGE):$(VERSION) and $(DOCKERHUB_IMAGE):local"
	@echo "Run with: docker run -p 5055:5055 -p 3000:3000 $(DOCKERHUB_IMAGE):local"

docker-push: docker-buildx-prepare
	@echo "📤 Building and pushing version $(VERSION) to both registries..."
	@echo "🔨 Building regular image..."
	docker buildx build --pull \
		--platform $(PLATFORMS) \
		--progress=plain \
		-t $(DOCKERHUB_IMAGE):$(VERSION) \
		-t $(GHCR_IMAGE):$(VERSION) \
		--push \
		.
	@echo "🔨 Building single-container image..."
	docker buildx build --pull \
		--platform $(PLATFORMS) \
		--progress=plain \
		-f Dockerfile.single \
		-t $(DOCKERHUB_IMAGE):$(VERSION)-single \
		-t $(GHCR_IMAGE):$(VERSION)-single \
		--push \
		.
	@echo "✅ Pushed version $(VERSION) to both registries (latest NOT updated)"

docker-push-latest: docker-buildx-prepare
	@echo "📤 Updating v1-latest tags to version $(VERSION)..."
	@echo "🔨 Building regular image with latest tag..."
	docker buildx build --pull \
		--platform $(PLATFORMS) \
		--progress=plain \
		-t $(DOCKERHUB_IMAGE):$(VERSION) \
		-t $(DOCKERHUB_IMAGE):v1-latest \
		-t $(GHCR_IMAGE):$(VERSION) \
		-t $(GHCR_IMAGE):v1-latest \
		--push \
		.
	@echo "🔨 Building single-container image with latest tag..."
	docker buildx build --pull \
		--platform $(PLATFORMS) \
		--progress=plain \
		-f Dockerfile.single \
		-t $(DOCKERHUB_IMAGE):$(VERSION)-single \
		-t $(DOCKERHUB_IMAGE):v1-latest-single \
		-t $(GHCR_IMAGE):$(VERSION)-single \
		-t $(GHCR_IMAGE):v1-latest-single \
		--push \
		.
	@echo "✅ Updated v1-latest to version $(VERSION)"

docker-release: docker-push-latest
	@echo "✅ Full release complete for version $(VERSION)"

tag:
	@version=$$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/'); \
	echo "Creating tag v$$version"; \
	git tag "v$$version"; \
	git push origin "v$$version"

export-docs:
	@echo "📚 Exporting documentation..."
	@uv run python scripts/export_docs.py
	@echo "✅ Documentation export complete!"

clean-cache:
	@echo "🧹 Cleaning cache directories..."
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name ".mypy_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name ".ruff_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -type f -delete 2>/dev/null || true
	@find . -name "*.pyo" -type f -delete 2>/dev/null || true
	@find . -name "*.pyd" -type f -delete 2>/dev/null || true
	@echo "✅ Cache directories cleaned!"
