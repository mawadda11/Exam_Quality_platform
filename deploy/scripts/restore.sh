#!/usr/bin/env bash
# Restore PostgreSQL and stored files from a backup made by backup.sh.
#
# Usage:
#   deploy/scripts/restore.sh \
#     --db-dump deploy/backups/<timestamp>/postgres.sql \
#     --uploads-archive deploy/backups/<timestamp>/uploads.tar.gz \
#     --reports-archive deploy/backups/<timestamp>/reports.tar.gz \
#     --confirm \
#     [path-to-env-file]
#
# All three --*-dump/--*-archive paths are required explicitly - this script
# never guesses "the latest backup" for you, and --confirm must be passed
# deliberately or nothing happens (a dry-run summary is printed instead).
# File restoration extracts archives additively into the running backend
# container's mounted volumes (tar overwrites/adds, it does not delete
# pre-existing files absent from the archive) - this script never runs DROP
# DATABASE or deletes any existing file itself.
#
# Restoring the SQL dump into a database that already has conflicting rows
# (e.g. the same primary keys) can fail with constraint errors rather than
# silently overwriting them - see docs/DEPLOYMENT.md's restore-drill section
# for the recommended fresh-database restore procedure.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/docker-compose.prod.yml"

log() { printf '[restore] %s\n' "$1"; }
fail() {
    printf '[restore] ERROR: %s\n' "$1" >&2
    exit 1
}

DB_DUMP=""
UPLOADS_ARCHIVE=""
REPORTS_ARCHIVE=""
CONFIRM=0
ENV_FILE=""

while [ $# -gt 0 ]; do
    case "$1" in
    --db-dump)
        DB_DUMP="$2"
        shift 2
        ;;
    --uploads-archive)
        UPLOADS_ARCHIVE="$2"
        shift 2
        ;;
    --reports-archive)
        REPORTS_ARCHIVE="$2"
        shift 2
        ;;
    --confirm)
        CONFIRM=1
        shift
        ;;
    -h | --help)
        sed -n '2,20p' "$0"
        exit 0
        ;;
    *)
        ENV_FILE="$1"
        shift
        ;;
    esac
done

ENV_FILE="${ENV_FILE:-$REPO_ROOT/.env.production}"
[ -f "$ENV_FILE" ] || fail "Env file not found: $ENV_FILE"
[ -n "$DB_DUMP" ] || fail "Missing required --db-dump <path>."
[ -n "$UPLOADS_ARCHIVE" ] || fail "Missing required --uploads-archive <path>."
[ -n "$REPORTS_ARCHIVE" ] || fail "Missing required --reports-archive <path>."
[ -f "$DB_DUMP" ] || fail "Not found: $DB_DUMP"
[ -f "$UPLOADS_ARCHIVE" ] || fail "Not found: $UPLOADS_ARCHIVE"
[ -f "$REPORTS_ARCHIVE" ] || fail "Not found: $REPORTS_ARCHIVE"

log "Restore plan:"
log "  PostgreSQL dump:  $DB_DUMP"
log "  Uploads archive:  $UPLOADS_ARCHIVE"
log "  Reports archive:  $REPORTS_ARCHIVE"
log "  Target env file:  $ENV_FILE"

if [ "$CONFIRM" -ne 1 ]; then
    log "Dry run only (no --confirm flag given) - nothing was restored."
    log "Re-run with --confirm once you have verified the plan above."
    exit 0
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
: "${POSTGRES_DB:?POSTGRES_DB missing from $ENV_FILE}"
: "${POSTGRES_USER:?POSTGRES_USER missing from $ENV_FILE}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD missing from $ENV_FILE}"

COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")

log "Restoring PostgreSQL database ($POSTGRES_DB)..."
"${COMPOSE[@]}" exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres \
    psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    <"$DB_DUMP" \
    || fail "Restoring the database failed - see the error above (a non-empty target database is a common cause; see docs/DEPLOYMENT.md)."

log "Restoring uploaded exams/TP-153 files..."
"${COMPOSE[@]}" exec -T backend tar xzf - -C /app/storage/uploads \
    <"$UPLOADS_ARCHIVE" \
    || fail "Restoring the uploads archive failed."

log "Restoring generated reports..."
"${COMPOSE[@]}" exec -T backend tar xzf - -C /app/storage/reports \
    <"$REPORTS_ARCHIVE" \
    || fail "Restoring the reports archive failed."

log "Restore complete. Run deploy/scripts/health-check.sh to verify the stack."
