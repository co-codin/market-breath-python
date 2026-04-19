IMAGE   ?= barchart-candles
SERVICE ?= barchart
REDIS   ?= redis
PORT    ?= 8000

.PHONY: help run install build up down restart logs shell ps redis-up redis-cli flush clean

help:
	@awk 'BEGIN{FS=":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

run: ## Run the server locally (expects a reachable Redis; see redis-up)
	HOST=127.0.0.1 PORT=$(PORT) uvicorn app.main:app --host 127.0.0.1 --port $(PORT) --reload

install: ## Install Python deps into the active environment
	pip install -r requirements.txt

build: ## Build the Docker image
	docker compose build

up: ## Start app + redis in the background
	docker compose up -d --build
	@echo "→ http://localhost:$(PORT)"

down: ## Stop and remove containers
	docker compose down

restart: down up ## Restart containers

logs: ## Tail app logs
	docker compose logs -f --tail=100 $(SERVICE)

shell: ## Open a shell in the running app container
	docker compose exec $(SERVICE) sh

ps: ## Show container status
	docker compose ps

redis-up: ## Start just the redis container (for local `make run`)
	docker compose up -d $(REDIS)

redis-cli: ## Open redis-cli in the redis container
	docker compose exec $(REDIS) redis-cli

flush: ## Flush the cache (FLUSHDB)
	docker compose exec $(REDIS) redis-cli FLUSHDB

clean: ## Remove containers and local images
	-docker compose down --rmi local --remove-orphans
