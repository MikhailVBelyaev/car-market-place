#!/bin/bash
set -e

echo "$(date) - 🟡 Starting scrape + model pipeline"

# Run scrape, capture output to temp log
TMP_LOG=$(mktemp)
python run_task_lacetti_white.py | tee "$TMP_LOG"

# Count newly saved cars from log
NEW_COUNT=$(grep "Saved car:" "$TMP_LOG" | wc -l)

if [ "$NEW_COUNT" -gt 0 ]; then
  echo "$(date) - ✅ $NEW_COUNT new cars saved. Proceeding to upload + train."

  # Upload to DBFS
  databricks fs cp /app/databricks/data/cars_latest.csv dbfs:/FileStore/cars_latest.csv --overwrite

  # Trigger Databricks job
  databricks jobs run-now --job-id "$TRAIN_JOB_ID"
else
  echo "$(date) - ⏭ No new data. Skipping model retrain."
fi
