# AI Companion Platform - Makefile
# Common commands for Docker operations

.PHONY: help build up down restart logs shell db-shell redis-shell clean test migrate

# Default target
help:
	@echo "AI Companion Platform - Docker Commands"
	@echo ""
	@echo "Available commands:"
	@echo "  make build       - Build all Docker images"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"
	@echo "  make restart     - Restart all services"
	@echo "  make logs        - View logs from all services"
	@echo "  make shell       - Open shell in API container"
	@echo "  make db-shell    - Open PostgreSQL shell"
	@echo "  make redis-shell - Open Redis CLI"
	@echo "  make clean       - Remove all containers, volumes, and images"
	@echo "  make test        - Run tests"
	@echo "  make migrate     - Run database migrations"
	@echo ""

# Build Docker images
build:
	docker-compose build

# Start all services
up:
	docker-compose up -d

# Start with logs
up-logs:
	docker-compose up

# Stop all services
down:
	docker-compose down

# Restart all services
restart:
	docker-compose restart

# View logs
logs:
	docker-compose logs -f

# View API logs only
logs-api:
	docker-compose logs -f api

# Open shell in API container
shell:
	docker-compose exec api /bin/sh

# Open PostgreSQL shell
db-shell:
	docker-compose exec postgres psql -U postgres -d ai_companion

# Open Redis CLI
redis-shell:
	docker-compose exec redis redis-cli -a redis_password

# Clean up everything
clean:
	docker-compose down -v --rmi all --remove-orphans

# Run tests
test:
	docker-compose exec api pytest

# Run database migrations
migrate:
	docker-compose --profile migration up migration

# Start with production profile (includes Nginx)
up-prod:
	docker-compose --profile production up -d

# Start with Celery workers
up-celery:
	docker-compose --profile celery up -d

# Check service health
health:
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health | jq .

# View resource usage
stats:
	docker stats ai-companion-api ai-companion-postgres ai-companion-redis
