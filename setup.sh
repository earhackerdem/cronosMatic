#!/usr/bin/env bash
set -euo pipefail

# ── Colors ───────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}   $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail()  { echo -e "${RED}[FAIL]${NC} $1"; }

# ── Required tools ───────────────────────────────────────
MISSING=0

check_required() {
  if command -v "$1" &>/dev/null; then
    ok "$1 found"
  else
    fail "$1 not found (required)"
    MISSING=1
  fi
}

check_optional() {
  if command -v "$1" &>/dev/null; then
    ok "$1 found"
  else
    warn "$1 not found (optional)"
  fi
}

echo ""
info "Checking required tools..."
check_required docker
check_required make

# Docker Compose v2 (docker compose, not docker-compose)
if docker compose version &>/dev/null; then
  ok "docker compose v2 found"
else
  fail "docker compose v2 not found (required)"
  MISSING=1
fi

echo ""
info "Checking optional tools..."
check_optional python3
check_optional node

# ── uv (Python package manager) ─────────────────────────
echo ""
if command -v uv &>/dev/null; then
  ok "uv found"
else
  info "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ok "uv installed"
fi

if [ "$MISSING" -eq 1 ]; then
  echo ""
  fail "Missing required tools. Please install them and retry."
  exit 1
fi

# ── Helper: generate random secret ──────────────────────
generate_secret() {
  LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 32 || true
}

# ── Generate .env ────────────────────────────────────────
echo ""
if [ -f .env ]; then
  info ".env already exists, skipping generation"
else
  cp .env.example .env

  # Replace placeholder secrets with random values
  PG_PASS=$(generate_secret)
  SECRET_KEY=$(generate_secret)

  sed -i.bak "s|POSTGRES_PASSWORD=change-me-in-production|POSTGRES_PASSWORD=${PG_PASS}|" .env
  sed -i.bak "s|BACKEND_SECRET_KEY=change-me-in-production|BACKEND_SECRET_KEY=${SECRET_KEY}|" .env
  rm -f .env.bak

  ok ".env created with generated secrets"
fi

# ── Validate .env defaults ──────────────────────────────
echo ""
info "Validating .env configuration..."

set -a
source .env
set +a

if [ "${POSTGRES_PASSWORD:-}" = "change-me-in-production" ]; then
  warn "POSTGRES_PASSWORD is still the example default — run: make setup-secrets"
fi
if [ "${BACKEND_SECRET_KEY:-}" = "change-me-in-production" ]; then
  warn "BACKEND_SECRET_KEY is still the example default — run: make setup-secrets"
fi

echo ""
ok "Setup complete!"
