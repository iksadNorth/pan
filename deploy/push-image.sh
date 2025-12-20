#!/bin/bash

set -e

IMAGE_NAME=${1:-api-server}
IMAGE_TAG=${2:-latest}
FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"
TAR_FILE="${IMAGE_NAME}-${IMAGE_TAG}-$(date +%s).tar"

docker build -t "${FULL_IMAGE_NAME}" -f Dockerfile .
docker save "${FULL_IMAGE_NAME}" -o "${TAR_FILE}"

sudo ctr -n k8s.io images import "${TAR_FILE}" || true

rm -f "${TAR_FILE}"
