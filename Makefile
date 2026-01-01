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
	@if [ ! -d venv ]; then \
		python3.11 -m venv venv; \
		echo "✓ Virtual environment created"; \
	fi
	@echo "Activating venv and installing dependencies..."
	@bash -c "source venv/bin/activate && pip install -r requirements.txt"
	@echo "✓ Dependencies installed"
	@echo ""
	@echo "Next steps:"
	@echo "1. source venv/bin/activate"
	@echo "2. Edit .env with your configuration"
	@echo "3. Run 'make migrate' to setup database"
	@echo "4. Run 'make run-bot' to start bot (lokal)"

# Install dependencies
install:
	@echo "Installing dependencies..."
	@pip install -r requirements.txt

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

# Local run commands (Docker'siz)
run-bot:
	@echo "Starting bot (local)..."
	@bash -c "source venv/bin/activate && python -m src.bot.app"

run-main:
	@echo "Starting main app (local)..."
	@bash -c "source venv/bin/activate && python -m src.main"

create-db:
	@echo "Creating database tables..."
	@bash -c "source venv/bin/activate && python -c 'import asyncio; from src.database.connection import get_async_engine; from src.database.models import Base; asyncio.run((lambda: get_async_engine().begin()).__call__()).run_sync(Base.metadata.create_all)' || python scripts/create_db.py"

# Docker Compose commands (agar Docker bo'lsa)
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
