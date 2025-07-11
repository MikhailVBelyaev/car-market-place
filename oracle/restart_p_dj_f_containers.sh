#!/bin/bash

if [ -d ~/.local/share/containers/storage/locks ]; then
  echo "🧼 Cleaning Podman locks..."
  rm -rf ~/.local/share/containers/storage/locks
  systemctl --user restart podman
  echo "🔁 Waiting for Podman to restart..."
  sleep 5
fi

echo "🛑 Stopping and removing existing container..."
podman rm -f postgres django frontend 2>/dev/null

echo "🧹 Removing old volumes..."
podman volume rm pgdata initdb 2>/dev/null

echo "📦 Creating new volumes..."
podman volume create pgdata
podman volume create initdb

echo "🚀 Creating car-marketplace-net network..."
podman network create car-marketplace-net 2>/dev/null

echo "🚀 Starting new postgres container..."
podman run -d \
  --name postgres \
  --network car-marketplace-net \
  -p 5432:5432 \
  --mount type=volume,source=pgdata,target=/var/lib/postgresql/data \
  --mount type=volume,source=initdb,target=/docker-entrypoint-initdb.d \
  -e POSTGRES_DB=postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  postgres_for_podman:latest

echo "⏳ Waiting for Postgres to be ready..."
until podman exec postgres pg_isready -U postgres >/dev/null 2>&1; do
  sleep 1
done
echo "✅ Postgres is ready."

echo "🚀 Starting new django container..."
podman run -d \
  --name django \
  --network car-marketplace-net \
  -p 8000:8000 \
  django_for_podman:latest

echo "⏳ Waiting for Django API to be ready..."
until curl -s http://localhost:8000/api/cars/ | head -c 10 | grep -q '\['; do
  sleep 1
done
echo "✅ Django API is responding."

echo "🚀 Starting new frontend container..."
podman run -d \
  --name frontend \
  --network car-marketplace-net \
  -p 8080:80 \
  -v /home/opc/nginx-config/nginx.conf:/etc/nginx/conf.d/default.conf:Z \
  frontend_for_podman:latest

echo "⏳ Waiting for Frontend to be ready..."
until curl -s http://localhost:8080/healthz >/dev/null; do
  sleep 1
done
echo "✅ Frontend is ready."

echo "✅ Containers started. Use 'podman ps' and 'podman logs -f <name>' to view status."
