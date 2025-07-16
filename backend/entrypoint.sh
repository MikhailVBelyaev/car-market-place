#!/bin/bash
set -e

python manage.py migrate

if [ ! -f /tmp/dump_loaded.lock ]; then
  echo "📦 Loading dump_cars.json"
  python manage.py upload_olx_dump /app/dump_cars.json
  touch /tmp/dump_loaded.lock
else
  echo "⚠️ Skipping dump load, already loaded (lock exists)"
fi


exec "$@"
