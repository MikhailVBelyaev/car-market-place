#!/usr/bin/env bash
#
# Publish one analytics post to the Telegram channel via the car-dev stack.
# Used by the host crontab (see scripts/install_channel_cron.sh).
#
# Usage:  post_to_channel.sh <post_type> [--dry-run]
#   post_type: brand_ranking | best_value | age_depreciation |
#              seasonal_trends | mileage_depreciation | weekly_digest
#
# Only spec-controlled, median-based posts are scheduled. The composition-noise
# posts (price_movers, color_premium, gear_premium) are intentionally excluded.

set -euo pipefail

POST_TYPE="${1:?usage: post_to_channel.sh <post_type> [--dry-run]}"
shift || true

PROJECT_DIR="/home/user/Projects/car-market-place"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.devlocal.yml"
LOG_DIR="${PROJECT_DIR}/logs"
mkdir -p "${LOG_DIR}"

TS="$(date '+%Y-%m-%d %H:%M:%S')"
echo "[${TS}] posting '${POST_TYPE}' $*" >> "${LOG_DIR}/channel_cron.log"

docker compose -f "${COMPOSE_FILE}" -p car-dev --profile channel \
  run --rm tg_channel "${POST_TYPE}" "$@" \
  >> "${LOG_DIR}/channel_cron.log" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] done '${POST_TYPE}' (exit $?)" >> "${LOG_DIR}/channel_cron.log"
