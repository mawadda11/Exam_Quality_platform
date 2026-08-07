#!/usr/bin/env bash
# Build and start the production/staging Compose stack.
#
# Usage:
#   deploy/scripts/deploy.sh [path-to-env-file]
#
# Defaults to <repo-root>/.env.production if no path is given. See
# docs/DEPLOYMENT.md for the full walkthrough. This script never prints the
# contents of the env file - only which required variables are present.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/docker-compose.prod.yml"
ENV_FILE="${1:-$REPO_ROOT/.env.production}"
HEALTH_PATH="/api/v1/health"
HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-120}"

log() { printf '[deploy] %s\n' "$1"; }
fail() {
    printf '[deploy] ERROR: %s\n' "$1" >&2
    exit 1
}

trap 'fail "deploy.sh exited early (see the error above); the stack may be partially started - re-run once the problem is fixed."' ERR

[ -f "$COMPOSE_FILE" ] || fail "Compose file not found: $COMPOSE_FILE"
[ -f "$ENV_FILE" ] || fail "Env file not found: $ENV_FILE (copy .env.production.example to $ENV_FILE and fill in every placeholder first)"

REQUIRED_VARS=(
    APP_ENV APP_DOMAIN CADDY_SITE_ADDRESS SECRET_KEY
    POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD DATABASE_URL
    VECTOR_STORE_PROVIDER CHROMA_HOST CHROMA_PORT
    ALLOWED_ORIGINS PASSWORD_RESET_URL
    AI_PROVIDER AI_MODEL OLLAMA_BASE_URL
    SMTP_HOST SMTP_FROM_EMAIL
)
log "Validating required environment variables in $ENV_FILE (values are never printed)..."
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

missing=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
        missing+=("$var")
    fi
done
if [ "${#missing[@]}" -gt 0 ]; then
    fail "Missing/empty required variable(s) in $ENV_FILE: ${missing[*]}"
fi

if [ "${SECRET_KEY}" = "replace-with-at-least-32-random-characters" ]; then
    fail "SECRET_KEY is still the .env.production.example placeholder - replace it before deploying."
fi
if [ "${POSTGRES_PASSWORD}" = "replace-with-a-strong-password" ]; then
    fail "POSTGRES_PASSWORD is still the .env.production.example placeholder - replace it before deploying."
fi
if [ "${#SECRET_KEY}" -lt 32 ]; then
    fail "SECRET_KEY must be at least 32 characters (matches backend/app/core/config.py:validate_runtime_settings)."
fi
if [ "${APP_ENV}" != "production" ] && [ "${APP_ENV}" != "staging" ]; then
    fail "APP_ENV must be 'production' or 'staging' for this stack, got: ${APP_ENV}"
fi
log "Required variables present."

COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")

log "Validating docker compose configuration..."
"${COMPOSE[@]}" config --quiet || fail "docker compose config failed - fix the reported error before continuing."

log "Building production images..."
"${COMPOSE[@]}" build

log "Running database migrations (alembic upgrade head)..."
"${COMPOSE[@]}" up migrate --exit-code-from migrate --abort-on-container-exit \
    || fail "Migrations failed - the stack was not started. Check 'docker compose -f $COMPOSE_FILE logs migrate'."

log "Initializing persistent storage ownership/permissions (storage-init)..."
"${COMPOSE[@]}" up storage-init --exit-code-from storage-init --abort-on-container-exit \
    || fail "Storage initialization failed - the stack was not started. Check 'docker compose -f $COMPOSE_FILE logs storage-init'."

log "Starting the production stack..."
"${COMPOSE[@]}" up -d --remove-orphans

log "Waiting for ${HEALTH_PATH} to report healthy (timeout: ${HEALTH_TIMEOUT_SECONDS}s)..."
site_address="${CADDY_SITE_ADDRESS%/}"
deadline=$((SECONDS + HEALTH_TIMEOUT_SECONDS))
until curl --silent --fail --max-time 5 "${site_address}${HEALTH_PATH}" >/dev/null 2>&1; do
    if [ "$SECONDS" -ge "$deadline" ]; then
        fail "Health check did not succeed within ${HEALTH_TIMEOUT_SECONDS}s. Run deploy/scripts/health-check.sh and check 'docker compose -f $COMPOSE_FILE logs'."
    fi
    sleep 3
done

log "Deployment complete. ${site_address}${HEALTH_PATH} is healthy."
log "Run deploy/scripts/health-check.sh for a fuller status summary."
