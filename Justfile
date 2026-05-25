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

# Tail all container logs
logs:
    docker compose logs -f

# Stop and remove all containers
down:
    docker compose down
