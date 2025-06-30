
#!/bin/bash
export DOCKER_DEFAULT_PLATFORM=linux/amd64


set -e

ARGS=("$@")

# Get ACR name from Terraform output (must be in current dir or adjust path)
ACR_NAME=$(terraform -chdir=./terraform output -raw acr_name)

build_and_push() {
  local name=$1
  local path=$2
  echo "🔧 Building $name image from $path..."
  docker build -t "$ACR_NAME.azurecr.io/$name:latest" "$path"

  echo "🚀 Pushing $name image to $ACR_NAME..."
  docker push "$ACR_NAME.azurecr.io/$name:latest"
}

echo "📦 Starting Docker image build and push process using ACR: $ACR_NAME.azurecr.io"

if [ ${#ARGS[@]} -eq 0 ]; then
  build_and_push django ./backend
  build_and_push frontend ./frontend
  build_and_push tg_bot ./tg_bot
  build_and_push scraper ./scraper
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