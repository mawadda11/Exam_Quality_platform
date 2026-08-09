#!/usr/bin/env bash
# Back up the production/staging PostgreSQL database, uploaded exams, and
# generated reports into a single timestamped directory.
#
# Usage:
#   deploy/scripts/backup.sh [path-to-env-file]
#
# Defaults to <repo-root>/.env.production. Backups are written under
# deploy/backups/ (gitignored, not served by Caddy/nginx/any web root, so
# never publicly reachable) rather than into storage/ or any directory the
# application itself serves.
#
# Retention: this script does not delete old backups automatically - that is
# an explicit operator decision (disk space and legal/institutional
# retention requirements vary by deployment). To prune backups older than N
# days yourself once you are ready to, e.g.:
#   find deploy/backups -maxdepth 1 -type d -mtime +30 -exec rm -rf {} +
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/docker-compose.prod.yml"
ENV_FILE="${1:-$REPO_ROOT/.env.production}"
BACKUP_ROOT="$REPO_ROOT/deploy/backups"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"

log() { printf '[backup] %s\n' "$1"; }
fail() {
    printf '[backup] ERROR: %s\n' "$1" >&2
    exit 1
}

[ -f "$ENV_FILE" ] || fail "Env file not found: $ENV_FILE"

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
: "${POSTGRES_DB:?POSTGRES_DB missing from $ENV_FILE}"
: "${POSTGRES_USER:?POSTGRES_USER missing from $ENV_FILE}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD missing from $ENV_FILE}"

COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
log "Writing backup to $BACKUP_DIR"

log "Dumping PostgreSQL database ($POSTGRES_DB)..."
# PGPASSWORD is only ever set inside this one non-interactive process's
# environment, passed straight to the postgres container - never printed,
# logged, or written to the dump file itself.
"${COMPOSE[@]}" exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
    pg_dump --format=plain --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    >"$BACKUP_DIR/postgres.sql" \
    || fail "pg_dump failed."

log "Archiving uploaded exams/TP-153 files (backend_uploads volume)..."
# Streamed through the already-running backend container (which already has
# the named volume mounted at /app/storage/uploads) rather than guessing
# Compose's project-prefixed volume name with a separate `docker run -v`,
# which is fragile if COMPOSE_PROJECT_NAME/the deployment directory name
# differs from the default assumption.
"${COMPOSE[@]}" exec -T backend tar czf - -C /app/storage/uploads . \
    >"$BACKUP_DIR/uploads.tar.gz" \
    || fail "Archiving the uploads volume failed (is the backend service running?)."

log "Archiving generated reports (backend_reports volume)..."
"${COMPOSE[@]}" exec -T backend tar czf - -C /app/storage/reports . \
    >"$BACKUP_DIR/reports.tar.gz" \
    || fail "Archiving the reports volume failed (is the backend service running?)."

log "Backup complete:"
log "  $BACKUP_DIR/postgres.sql"
log "  $BACKUP_DIR/uploads.tar.gz"
log "  $BACKUP_DIR/reports.tar.gz"
