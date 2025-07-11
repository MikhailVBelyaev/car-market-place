

#!/bin/bash
export DOCKER_DEFAULT_PLATFORM=linux/amd64

set -e

ARGS=("$@")

# GCP Artifact Registry parameters
PROJECT_ID="car-market-place-1231"
REGION="us-central1"
REPO_NAME="car-marketplace-repo"

REPO_URL="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME"

build_and_push() {
  local name=$1
  local path=$2
  echo "🔧 Building $name image from $path..."
  docker build -t "$REPO_URL/$name:latest" "$path"

  echo "🚀 Pushing $name image to $REPO_URL..."
  docker push "$REPO_URL/$name:latest"
}

echo "📦 Starting Docker image build and push process using GCP Artifact Registry: $REPO_URL"

if [ ${#ARGS[@]} -eq 0 ]; then
  build_and_push django ./backend
  build_and_push frontend ./frontend
  build_and_push tg_bot ./tg_bot
  build_and_push scraper ./scraper
  build_and_push extract-data ./extract_data
  build_and_push postgres ./db
else
  for arg in "${ARGS[@]}"; do
    case "$arg" in
      django)
        build_and_push django ./backend
        ;;
      frontend)
        build_and_push frontend ./frontend
        ;;
      tg_bot)
        build_and_push tg_bot ./tg_bot
        ;;
      scraper)
        build_and_push scraper ./scraper
        ;;
      extract-data)
        build_and_push extract-data ./extract_data
        ;;
      postgres)
        build_and_push postgres ./db
        ;;
      *)
        echo "❌ Unknown service: $arg"
        ;;
    esac
  done
fi

echo "✅ All images built and pushed successfully."