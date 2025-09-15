#!/bin/bash
export DOCKER_DEFAULT_PLATFORM=linux/amd64

set -e

ARGS=("$@")

# 🖥️ Change this to your local server's user@ip
TARGET_SERVER="user@192.168.100.194"

build_and_deploy() {
  local name=$1
  local path=$2
  local image_name="${name}"

  if [ "$name" = "ngrok" ]; then
    ssh "$TARGET_SERVER" "mkdir -p ~/Projects/car-market-place/ngrok"

    echo "📤 Copying docker-compose_local.yml to $TARGET_SERVER as docker-compose.yml..."
    scp "docker-compose_local.yml" "$TARGET_SERVER:~/Projects/car-market-place/docker-compose.yml"

    echo "📤 Copying ngrok/.env to $TARGET_SERVER..."
    scp "$path/.env" "$TARGET_SERVER:~/Projects/car-market-place/ngrok/.env"

    echo "🚀 Starting ngrok service on $TARGET_SERVER..."
    ssh "$TARGET_SERVER" "cd ~/Projects/car-market-place && docker compose up -d ngrok"
    return
  fi

  echo "🔧 Building image: $image_name from $path..."
  docker build -t "$image_name" "$path"

  echo "💾 Saving $image_name to $image_name.tar..."
  docker save --output="${image_name}.tar" "$image_name"

  ssh "$TARGET_SERVER" "mkdir -p ~/Projects/car-market-place"

  echo "📤 Copying docker-compose_local.yml to $TARGET_SERVER as docker-compose.yml..."
  scp "docker-compose_local.yml" "$TARGET_SERVER:~/Projects/car-market-place/docker-compose.yml"

  echo "📤 Copying ${image_name}.tar and any .env files to $TARGET_SERVER..."
  ssh "$TARGET_SERVER" "mkdir -p ~/Projects/car-market-place"
  scp "${image_name}.tar" "$TARGET_SERVER:~/Projects/car-market-place/"

  # Copy service-specific .env if exists
  if [ "$name" = "django" ]; then
    if [ -f "$path/car_marketplace/.env" ]; then
      echo "📤 Copying backend/car_marketplace/.env to $TARGET_SERVER:~/Projects/car-market-place/backend/car_marketplace/.env"
      ssh "$TARGET_SERVER" "mkdir -p ~/Projects/car-market-place/backend/car_marketplace"
      scp "$path/car_marketplace/.env" "$TARGET_SERVER:~/Projects/car-market-place/backend/car_marketplace/.env"
    fi
  elif [ "$name" = "postgres" ]; then
    if [ -f "$path/.env" ]; then
      echo "📤 Copying db/.env to $TARGET_SERVER:~/Projects/car-market-place/db/.env"
      ssh "$TARGET_SERVER" "mkdir -p ~/Projects/car-market-place/db"
      scp "$path/.env" "$TARGET_SERVER:~/Projects/car-market-place/db/.env"
    fi
  elif [ -f "$path/.env" ]; then
    ssh "$TARGET_SERVER" "mkdir -p ~/Projects/car-market-place"
    scp "$path/.env" "$TARGET_SERVER:~/Projects/car-market-place/${name}.env"
  fi

  echo "📥 Loading ${image_name}.tar on $TARGET_SERVER..."
  ssh "$TARGET_SERVER" "cd ~/Projects/car-market-place && docker load -i ${image_name}.tar && rm ${image_name}.tar"
  ssh "$TARGET_SERVER" "cd ~/Projects/car-market-place && docker compose up -d $name"
}

echo "📦 Starting Docker image build and deploy process to $TARGET_SERVER..."

if [ ${#ARGS[@]} -eq 0 ]; then
  build_and_deploy django ./backend
  build_and_deploy frontend ./frontend
  build_and_deploy tg_bot ./tg_bot
  build_and_deploy scraper ./scraper
  build_and_deploy ml_api ./ml_api
  build_and_deploy extract_data ./extract_data
  build_and_deploy postgres ./db
else
  for arg in "${ARGS[@]}"; do
    case "$arg" in
      django)
        build_and_deploy django ./backend
        ;;
      frontend)
        build_and_deploy frontend ./frontend
        ;;
      tg_bot)
        build_and_deploy tg_bot ./tg_bot
        ;;
      scraper)
        build_and_deploy scraper ./scraper
        ;;
      extract-data | extract_data)
        build_and_deploy extract_data ./extract_data
        ;;
      ml_api)
        build_and_deploy ml_api ./ml_api
        ;;
      postgres)
        build_and_deploy postgres ./db
        ;;
      ngrok)
        build_and_deploy ngrok ./ngrok
        ;;
      *)
        echo "❌ Unknown service: $arg"
        ;;
    esac
  done
fi

echo "✅ All images built, copied, and loaded successfully on $TARGET_SERVER."