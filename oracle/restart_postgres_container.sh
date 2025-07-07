#!/bin/bash

echo "🛑 Stopping and removing existing container..."
podman rm -f postgres 2>/dev/null

echo "🧹 Removing old volumes..."
podman volume rm pgdata initdb 2>/dev/null

echo "📦 Creating new volumes..."
podman volume create pgdata
podman volume create initdb

echo "🚀 Starting new postgres container..."
podman run -d \
  --name postgres \
  -p 5432:5432 \
  --mount type=volume,source=pgdata,target=/var/lib/postgresql/data \
  --mount type=volume,source=initdb,target=/docker-entrypoint-initdb.d \
  -e POSTGRES_DB=postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  postgres_for_podman:latest

echo "✅ Container started. Use 'podman logs -f postgres' to view logs."
