.PHONY: help setup install migrate upgrade downgrade start stop restart logs shell test clean

# Default target
help:
	@echo "GroupPulse - Available Commands:"
	@echo ""
	@echo "  make setup       - Initial project setup (install deps, create .env, init DB)"
	@echo "  make install     - Install Python dependencies"
	@echo "  make migrate     - Run database migrations"
	@echo "  make upgrade     - Upgrade database to latest migration"
	@echo "  make downgrade   - Downgrade database by one migration"
	@echo ""
	@echo "  make start       - Start all services (Docker Compose)"
	@echo "  make stop        - Stop all services"
	@echo "  make restart     - Restart all services"
	@echo "  make logs        - View logs (follow mode)"
	@echo "  make shell       - Open database shell"
	@echo ""
	@echo "  make test        - Run tests"
	@echo "  make clean       - Clean up temporary files"
	@echo ""

# Initial setup
setup:
	@echo "Setting up GroupPulse..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✓ Created .env file - please edit with your credentials"; \
	fi
	@poetry install
	@echo "✓ Dependencies installed"
	@echo ""
	@echo "Next steps:"
	@echo "1. Edit .env with your configuration"
	@echo "2. Run 'make migrate' to setup database"
	@echo "3. Run 'make start' to start services"

# Install dependencies
install:
	@echo "Installing dependencies..."
	@poetry install

# Database migrations
migrate:
	@echo "Running database migrations..."
	@docker-compose exec -T postgres psql -U grouppulse -d grouppulse -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
	@alembic upgrade head
	@echo "✓ Database migrated"

upgrade:
	@echo "Upgrading database..."
	@alembic upgrade head

downgrade:
	@echo "Downgrading database..."
	@alembic downgrade -1

# Docker Compose commands
start:
	@echo "Starting GroupPulse services..."
	@docker-compose up -d
	@echo "✓ Services started"
	@echo "Use 'make logs' to view logs"

stop:
	@echo "Stopping GroupPulse services..."
	@docker-compose down
	@echo "✓ Services stopped"

restart:
	@echo "Restarting GroupPulse services..."
	@docker-compose restart
	@echo "✓ Services restarted"

logs:
	@docker-compose logs -f

# Database shell
shell:
	@docker-compose exec postgres psql -U grouppulse -d grouppulse

# Testing
test:
	@echo "Running tests..."
	@pytest tests/ -v

# Cleanup
clean:
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleanup complete"
