#!/bin/bash

IMAGE_TAR=~/postgres_for_podman.tar
IMAGE_NAME=postgres_for_podman

echo "🌀 Loading image from $IMAGE_TAR..."
podman load -i "$IMAGE_TAR"

echo "🧼 Cleaning up old dangling images..."
# This removes untagged/dangling images (optional)
podman image prune -f

echo "🧹 Removing older versions of $IMAGE_NAME (except latest)..."
# List and remove older versions of the same image, except "latest"
OLD_IMAGES=$(podman images --format "{{.Repository}}:{{.Tag}} {{.ID}}" | grep "$IMAGE_NAME" | grep -v "latest" | awk '{print $2}')

for img_id in $OLD_IMAGES; do
  podman rmi -f "$img_id"
done

echo "✅ Image loaded and cleanup completed."
