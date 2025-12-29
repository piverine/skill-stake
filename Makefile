# Skill-Stake Learning Platform Makefile

.PHONY: help setup up down logs clean install-backend install-frontend migrate test

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Set up the development environment
	@echo "Setting up development environment..."
	@cp .env.example .env || echo ".env already exists"
	@cp frontend/.env.local.example frontend/.env.local || echo "frontend/.env.local already exists"
	@echo "Please edit .env and frontend/.env.local with your API keys"

up: ## Start all services with Docker Compose
	docker-compose up -d

down: ## Stop all services
	docker-compose down

logs: ## Show logs from all services
	docker-compose logs -f

clean: ## Clean up Docker containers and volumes
	docker-compose down -v
	docker system prune -f

install-backend: ## Install backend dependencies locally
	cd backend && pip install -r requirements.txt

install-frontend: ## Install frontend dependencies locally
	cd frontend && npm install

migrate: ## Run database migrations
	docker-compose exec backend alembic upgrade head

migrate-local: ## Run database migrations locally
	cd backend && alembic upgrade head

test-backend: ## Run backend tests
	cd backend && python -m pytest

test-frontend: ## Run frontend tests
	cd frontend && npm test

dev-backend: ## Run backend in development mode locally
	cd backend && uvicorn app.main:app --reload

dev-frontend: ## Run frontend in development mode locally
	cd frontend && npm run dev

build: ## Build all Docker images
	docker-compose build

restart: ## Restart all services
	docker-compose restart