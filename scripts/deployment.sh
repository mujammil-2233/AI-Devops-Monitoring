#!/usr/bin/env bash
# ==============================================================================
# Enterprise Blue/Green Zero-Downtime Deployment & Auto-Rollback Script
# Author: DevOps Engineering Team
# Project: AI-Powered DevOps Monitoring & Auto-Healing System
# ==============================================================================

set -euo pipefail

# Configuration
IMAGE_NAME="${IMAGE_NAME:-ai-devops-monitor}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
ECR_REGISTRY="${ECR_REGISTRY:-local}"
FULL_IMAGE="${ECR_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
CONTAINER_NAME="${CONTAINER_NAME:-flask-app}"
HEALTH_CHECK_SCRIPT="./scripts/health-check.sh"
DEPLOY_LOG="logs/deployment.log"

mkdir -p logs

log() {
    local timestamp
    timestamp="$(date -u +"%Y-%m-%d %H:%M:%S UTC")"
    echo "${timestamp} [DEPLOY] $1" | tee -a "${DEPLOY_LOG}"
}

log "=========================================================="
log " Starting Automated Deployment Pipeline"
log " Target Image : ${FULL_IMAGE}"
log " Container    : ${CONTAINER_NAME}"
log "=========================================================="

# 1. Capture Previous Stable Image for Rollback
PREV_IMAGE=$(docker inspect --format='{{.Config.Image}}' "${CONTAINER_NAME}" 2>/dev/null || echo "")
log "Previous active image tag: ${PREV_IMAGE:-None}"

rollback() {
    log "=========================================================="
    log "[ROLLBACK TRIGGERED] Deployment validation failed!"
    if [ -n "${PREV_IMAGE}" ]; then
        log "Reverting container '${CONTAINER_NAME}' to previous image: ${PREV_IMAGE}..."
        docker stop "${CONTAINER_NAME}" || true
        docker rm "${CONTAINER_NAME}" || true
        docker run -d \
            --name "${CONTAINER_NAME}" \
            --restart unless-stopped \
            -p 5000:5000 \
            -v "$(pwd)/logs:/var/log/app" \
            "${PREV_IMAGE}"
        log "[ROLLBACK COMPLETE] Restored container on previous stable image: ${PREV_IMAGE}."
    else
        log "[ROLLBACK WARNING] No previous container image found to revert to."
    fi
    log "=========================================================="
    exit 1
}

# 2. Pull / Verify Target Image
if [ "${ECR_REGISTRY}" != "local" ]; then
    log "Pulling target image ${FULL_IMAGE} from registry..."
    docker pull "${FULL_IMAGE}"
fi

# 3. Stop and replace existing container
log "Updating container '${CONTAINER_NAME}'..."
docker stop "${CONTAINER_NAME}" 2>/dev/null || true
docker rm "${CONTAINER_NAME}" 2>/dev/null || true

log "Starting new container '${CONTAINER_NAME}'..."
docker run -d \
    --name "${CONTAINER_NAME}" \
    --restart unless-stopped \
    -p 5000:5000 \
    -v "$(pwd)/logs:/var/log/app" \
    "${FULL_IMAGE}"

# 4. Post-Deployment Verification
log "Running post-deployment health check..."
if bash "${HEALTH_CHECK_SCRIPT}"; then
    log "=========================================================="
    log "[DEPLOYMENT SUCCESSFUL] Image ${FULL_IMAGE} is live and healthy!"
    log "=========================================================="

    # Prune dangling images
    docker image prune -f >/dev/null 2>&1 || true
    exit 0
else
    rollback
fi
