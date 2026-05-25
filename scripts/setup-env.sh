#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"
ENV_EXAMPLE="$ROOT_DIR/.env.example"

if [ ! -f "$ENV_FILE" ]; then
    echo "Creating .env from .env.example..."
    cp "$ENV_EXAMPLE" "$ENV_FILE"
fi

if grep -q "=changethis$" "$ENV_FILE"; then
    echo "Generating secrets for changethis placeholders..."
    TMP_FILE=$(mktemp)
    while IFS= read -r line || [ -n "$line" ]; do
        if echo "$line" | grep -qE '^[A-Za-z_][A-Za-z0-9_]*=changethis$'; then
            KEY=$(echo "$line" | cut -d= -f1)
            SECRET=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
            printf '%s=%s\n' "$KEY" "$SECRET"
        else
            printf '%s\n' "$line"
        fi
    done < "$ENV_FILE" > "$TMP_FILE"
    mv "$TMP_FILE" "$ENV_FILE"
    echo "Secrets generated."
else
    echo "All secrets already set — skipping generation."
fi
