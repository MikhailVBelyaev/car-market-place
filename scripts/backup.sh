#!/bin/bash
# ==============================================================
# Car Marketplace — Production Backup Script
#
# What it does:
#   1. pg_dump from the running postgres container
#   2. Tar all .env / settings files
#   3. Rotate backups older than KEEP_DAYS
#
# Setup (run once on the production server):
#   mkdir -p ~/backups/car_marketplace
#   chmod +x ~/Projects/car-market-place/scripts/backup.sh
#
# Add to crontab (crontab -e):
#   0 2 * * * /home/user/Projects/car-market-place/scripts/backup.sh >> /home/user/backups/car_marketplace/backup.log 2>&1
# ==============================================================

set -euo pipefail

# ===== CONFIG =====
PROJECT_DIR="/home/user/Projects/car-market-place"
BACKUP_DIR="/home/user/backups/car_marketplace"

DB_USER="marketplace_user"
DB_NAME="postgres"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"

TIMESTAMP=$(date +%F_%H-%M)
DB_DUMP="$BACKUP_DIR/db_${TIMESTAMP}.dump"
ENV_ARCHIVE="$BACKUP_DIR/settings_${TIMESTAMP}.tar.gz"
LOG_PREFIX="[$(date '+%F %T')]"

# ===== HELPERS =====
log()  { echo "$LOG_PREFIX $*"; }
ok()   { echo "$LOG_PREFIX OK  $*"; }
fail() { echo "$LOG_PREFIX ERR $*" >&2; exit 1; }

# ===== PREFLIGHT =====
log "=== Backup started ==="

mkdir -p "$BACKUP_DIR"

cd "$PROJECT_DIR" || fail "Project dir not found: $PROJECT_DIR"

# Check that the postgres container is running
POSTGRES_ID=$(docker compose -f "$COMPOSE_FILE" ps -q postgres 2>/dev/null)
if [ -z "$POSTGRES_ID" ]; then
  fail "postgres container is not running — aborting"
fi

# ===== 1. DATABASE DUMP =====
log "Creating pg_dump..."

docker compose -f "$COMPOSE_FILE" exec -T postgres \
  pg_dump -U "$DB_USER" -F c -b "$DB_NAME" \
  > "$DB_DUMP"

if [ -s "$DB_DUMP" ]; then
  SIZE=$(du -sh "$DB_DUMP" | cut -f1)
  ok "Database dump saved: $DB_DUMP ($SIZE)"
else
  rm -f "$DB_DUMP"
  fail "pg_dump produced an empty file — check postgres logs"
fi

# ===== 2. SETTINGS / ENV FILES =====
log "Archiving .env files..."

# Collect only the files that actually exist
ENV_FILES=()
for f in \
  "$PROJECT_DIR/backend/car_marketplace/.env" \
  "$PROJECT_DIR/db/.env" \
  "$PROJECT_DIR/tg_bot/.env" \
  "$PROJECT_DIR/ngrok/.env"
do
  [ -f "$f" ] && ENV_FILES+=("$f")
done

if [ ${#ENV_FILES[@]} -eq 0 ]; then
  log "WARNING: no .env files found — skipping settings archive"
else
  tar -czf "$ENV_ARCHIVE" "${ENV_FILES[@]}"
  ok "Settings archived: $ENV_ARCHIVE (${#ENV_FILES[@]} files)"
fi

# ===== 3. SUMMARY =====
TOTAL=$(find "$BACKUP_DIR" -maxdepth 1 \( -name "db_*.dump" -o -name "settings_*.tar.gz" \) | wc -l)
log "=== Backup complete — $TOTAL file(s) in $BACKUP_DIR ==="
