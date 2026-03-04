# CronosMatic

Sistema de gestión de turnos inteligente.

## Prerequisites

- Docker & Docker Compose v2
- Make
- (Opcional) Python 3, Node.js

## Quick Start

```bash
make setup    # Valida herramientas y genera .env
make up       # Levanta los servicios
make logs     # Ver logs en tiempo real
make down     # Detener servicios
```

## Estructura del proyecto

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

## Comandos disponibles

Ejecuta `make help` para ver todos los comandos.
