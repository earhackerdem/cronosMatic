# List all available recipes
default:
    @just --list

# Bootstrap local environment: generate secrets, build images, and start containers
setup:
    @bash scripts/setup-env.sh
    docker compose up --build -d

# Run backend test suite with coverage
test:
    docker compose exec backend bash scripts/test.sh

# Run linters (mypy, ruff check)
lint:
    docker compose exec backend bash scripts/lint.sh

# Run code formatter (ruff format)
format:
    docker compose exec backend bash scripts/format.sh

# Generate an Alembic migration (usage: just db-makemigrations "message")
db-makemigrations message:
    docker compose exec backend alembic revision --autogenerate -m "{{message}}"

# Apply all pending Alembic migrations
db-migrate:
    docker compose exec backend alembic upgrade head

# Recreate containers to pick up changes in .env (compose only re-reads env_file on create, not restart)
env-reload:
    docker compose up -d

# Rebuild and restart a single service (use after backend code changes when not running `just watch`).
# Usage: just rebuild backend
rebuild service:
    docker compose up -d --build {{service}}

# Live-sync local source into containers using compose develop.watch (runs in foreground)
watch:
    docker compose watch

# Tail all container logs
logs:
    docker compose logs -f

# Stop and remove all containers
down:
    docker compose down
