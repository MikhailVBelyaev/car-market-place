#!/bin/bash

# ===== CONFIG =====
REMOTE_USER="user"
REMOTE_HOST="100.69.53.111"
REMOTE_PROJECT_DIR="/home/user/Projects/car-market-place"  # remote project folder
REMOTE_DUMP_NAME="backup.dump"
LOCAL_DEST="./backup_remote_$(date +%F_%H-%M).dump"

# ===== STEPS =====
echo "📦 Creating dump on remote host $REMOTE_HOST..."

ssh ${REMOTE_USER}@${REMOTE_HOST} bash -c "'
cd ${REMOTE_PROJECT_DIR} || exit 1
docker compose exec postgres pg_dump -U marketplace_user -F c -b -v -f /var/lib/postgresql/data/${REMOTE_DUMP_NAME} postgres
docker cp \$(docker compose ps -q postgres):/var/lib/postgresql/data/${REMOTE_DUMP_NAME} ${REMOTE_PROJECT_DIR}/${REMOTE_DUMP_NAME}
'"

echo "📥 Copying remote dump to local machine..."
scp ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PROJECT_DIR}/${REMOTE_DUMP_NAME} ${LOCAL_DEST}

if [ $? -eq 0 ]; then
    echo "✅ Remote dump copied successfully to $LOCAL_DEST"
else
    echo "❌ Failed to copy remote dump"
fi