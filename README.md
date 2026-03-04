# CronosMatic

Intelligent shift management system.

## Prerequisites

- Docker & Docker Compose v2
- Make
- (Optional) Python 3, Node.js

## Quick Start

```bash
make setup    # Validates tools and generates .env
make up       # Starts services
make logs     # View real-time logs
make down     # Stops services
```

## Project structure

```
cronosMatic/
├── backend/          # FastAPI + SQLAlchemy
├── frontend/         # Angular 19+
├── docker-compose.yml
├── Makefile
├── setup.sh
├── .env.example
└── README.md
```

## Available commands

Run `make help` to see all available commands.
