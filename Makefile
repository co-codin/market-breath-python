IMAGE   ?= barchart-candles
SERVICE ?= barchart
PORT    ?= 8000

.PHONY: help run build up down restart logs shell ps clean

help:
	@awk 'BEGIN{FS=":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

run: ## Run the server locally (no Docker)
	HOST=127.0.0.1 PORT=$(PORT) python3 server.py

build: ## Build the Docker image
	docker compose build

up: ## Start the container in the background
	docker compose up -d --build
	@echo "→ http://localhost:$(PORT)"

down: ## Stop and remove the container
	docker compose down

restart: down up ## Restart the container

logs: ## Tail container logs
	docker compose logs -f --tail=100 $(SERVICE)

shell: ## Open a shell in the running container
	docker compose exec $(SERVICE) sh

ps: ## Show container status
	docker compose ps

clean: ## Remove container and image
	-docker compose down --rmi local --remove-orphans
