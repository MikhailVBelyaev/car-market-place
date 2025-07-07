

#!/bin/bash
export DOCKER_DEFAULT_PLATFORM=linux/amd64

set -e

ARGS=("$@")

build_and_save() {
  local name=$1
  local path=$2
  local image_name="${name}_for_podman"

  echo "🔧 Building image: $image_name from $path..."
  docker build -t "$image_name" "$path"

  echo "💾 Saving $image_name to $image_name.tar..."
  docker save --output="${image_name}.tar" "$image_name"

  echo "📤 Copying ${image_name}.tar to remote server (OPC)..."
  scp -i ~/Downloads/ssh-key-2025-07-03.key "${image_name}.tar" opc@129.80.137.29:~
}

echo "📦 Starting Docker image build and save process for Podman..."

if [ ${#ARGS[@]} -eq 0 ]; then
  build_and_save django ./backend
  build_and_save frontend ./frontend
  build_and_save tg_bot ./tg_bot
  build_and_save scraper ./scraper
  build_and_save extract_data ./extract_data
  build_and_save postgres ./db
else
  for arg in "${ARGS[@]}"; do
    case "$arg" in
      django)
        build_and_save django ./backend
        ;;
      frontend)
        build_and_save frontend ./frontend
        ;;
      tg_bot)
        build_and_save tg_bot ./tg_bot
        ;;
      scraper)
        build_and_save scraper ./scraper
        ;;
      extract-data | extract_data)
        build_and_save extract_data ./extract_data
        ;;
      postgres)
        build_and_save postgres ./db
        ;;
      *)
        echo "❌ Unknown service: $arg"
        ;;
    esac 
  done
fi

echo "✅ All images built and saved as tarballs successfully."