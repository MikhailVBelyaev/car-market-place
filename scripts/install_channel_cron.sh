#!/usr/bin/env bash
#
# Install (idempotently) the host crontab entries that publish channel posts.
# Re-running replaces the managed block, so it is safe to run repeatedly.
#
# Schedule (matches airflow/dags/tg_channel_dag.py):
#   Mon 09:00 → brand_ranking        (market share)
#   Wed 09:00 → best_value           (real below-median deals, last 7d)
#   Fri 09:00 → age_depreciation     (per-model median curve)
#   1st 09:00 → seasonal_trends      (per-model monthly median)
#   15th 09:00 → mileage_depreciation ($/10k km per model)

set -euo pipefail

SCRIPT="/home/user/Projects/car-market-place/scripts/post_to_channel.sh"
MARK_BEGIN="# >>> uzvehicles channel posts >>>"
MARK_END="# <<< uzvehicles channel posts <<<"

BLOCK="$(cat <<EOF
${MARK_BEGIN}
0 9 * * 1 ${SCRIPT} brand_ranking
0 9 * * 3 ${SCRIPT} best_value
0 9 * * 5 ${SCRIPT} age_depreciation
0 9 1 * * ${SCRIPT} seasonal_trends
0 9 15 * * ${SCRIPT} mileage_depreciation
${MARK_END}
EOF
)"

# Strip any previous managed block, then append the fresh one.
CURRENT="$(crontab -l 2>/dev/null || true)"
CLEANED="$(printf '%s\n' "${CURRENT}" | sed "/${MARK_BEGIN}/,/${MARK_END}/d")"

printf '%s\n%s\n' "${CLEANED}" "${BLOCK}" | sed '/^$/N;/^\n$/D' | crontab -

echo "Installed channel cron. Current entries:"
crontab -l | sed -n "/${MARK_BEGIN}/,/${MARK_END}/p"
