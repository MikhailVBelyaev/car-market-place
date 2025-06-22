#!/bin/bash
set -e

python manage.py migrate

# Only load the dump if no cars exist (idempotent)
if [ "$(python manage.py shell -c 'from cars.models import Car; print(Car.objects.count())')" == "0" ]; then
  echo "📦 Loading dump_cars.json"
  python manage.py loaddata /app/db/dump_cars.json
fi

exec "$@"
