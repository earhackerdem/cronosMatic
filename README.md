# CronosMatic

Intelligent shift management system.

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, TypeScript 5.9, Vite 7, React Router 7 |
| **Frontend Testing** | Vitest, Testing Library, jsdom |
| **Backend** | FastAPI, Python 3.12+, Pydantic Settings |
| **ORM / DB** | SQLAlchemy 2 (async), asyncpg, PostgreSQL 17 + pgvector |
| **Migrations** | Alembic |
| **Backend Testing** | pytest, pytest-asyncio, httpx |
| **Linting** | ESLint (frontend), Ruff (backend) |
| **Infrastructure** | Docker Compose, pgAdmin 4 |

## Prerequisites

- Docker & Docker Compose v2
- Make
- (Optional) Python 3.12+, Node.js, [uv](https://docs.astral.sh/uv/)

## Quick Start

```bash
make setup    # Validates tools, installs uv, generates .env with random secrets
make up       # Starts all services (db, backend, frontend, pgadmin)
```

The app will be available at:
- **Frontend:** http://localhost:4200
- **Backend API:** http://localhost:8000
- **pgAdmin:** http://localhost:5050

## Project Structure

```
cronosMatic/
├── backend/          # FastAPI + SQLAlchemy (async)
├── frontend/         # React + Vite + TypeScript
├── docker/           # Docker-specific config (pgAdmin servers.json)
├── docker-compose.yml
├── Makefile
├── setup.sh
├── .env.example
└── README.md
```

## Available Commands

### Setup

| Command | Description |
|---|---|
| `make setup` | Run setup.sh (validate tools, generate .env with secrets) + git init |
| `make setup-secrets` | Regenerate `POSTGRES_PASSWORD` and `BACKEND_SECRET_KEY` in .env |

### Docker

| Command | Description |
|---|---|
| `make up` | Start all services |
| `make down` | Stop all services |
| `make build` | Rebuild images |
| `make logs` | View logs for all services |
| `make status` | Show services status |
| `make clean` | Stop services and remove volumes |

### Database

| Command | Description |
|---|---|
| `make db-migrate` | Run Alembic migrations |
| `make db-revision MSG="description"` | Create new migration |
| `make db-admin` | Show pgAdmin connection info |

### Tests

| Command | Description |
|---|---|
| `make test` | Run all tests (backend + frontend) |
| `make test-back` | Run backend tests (pytest) |
| `make test-front` | Run frontend tests (vitest) |
