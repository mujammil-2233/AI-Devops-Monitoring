#!/usr/bin/env bash
# ==============================================================================
# Health Check Verification Script
# Validates Flask Application Readiness, Liveness, and Prometheus Telemetry
# Author: DevOps Engineering Team
# ==============================================================================

set -euo pipefail

# Configuration
APP_HOST="${APP_HOST:-localhost}"
APP_PORT="${APP_PORT:-5000}"
HEALTH_URL="http://${APP_HOST}:${APP_PORT}/health"
METRICS_URL="http://${APP_HOST}:${APP_PORT}/metrics"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-10}"
SLEEP_INTERVAL="${SLEEP_INTERVAL:-3}"

echo "=========================================================="
echo " Starting Application Health Check Probe"
echo " Target Endpoint : ${HEALTH_URL}"
echo " Metrics Endpoint: ${METRICS_URL}"
echo " Max Attempts    : ${MAX_ATTEMPTS}"
echo "=========================================================="

attempt=1
while [ "${attempt}" -le "${MAX_ATTEMPTS}" ]; do
    echo "[Attempt ${attempt}/${MAX_ATTEMPTS}] Probing ${HEALTH_URL}..."

    # Probe HTTP status code
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "${HEALTH_URL}" 2>/dev/null || true)
    if [ -z "${HTTP_STATUS}" ] || [ "${HTTP_STATUS}" = "000" ]; then
        HTTP_STATUS="000"
    fi

    if [ "${HTTP_STATUS}" = "200" ]; then
        echo "[SUCCESS] Health endpoint returned HTTP 200 (OK)."

        # Validate Prometheus metrics endpoint
        METRICS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "${METRICS_URL}" 2>/dev/null || true)
        if [ "${METRICS_STATUS}" = "200" ]; then
            echo "[SUCCESS] Metrics endpoint returned HTTP 200 (Prometheus Ready)."
            echo "=========================================================="
            echo " Application is 100% HEALTHY and OPERATIONAL."
            echo "=========================================================="
            exit 0
        else
            echo "[WARNING] Health endpoint is UP, but /metrics returned HTTP ${METRICS_STATUS}."
        fi
    else
        echo "[FAILURE] Health endpoint returned HTTP ${HTTP_STATUS} (Expected 200)."
    fi

    if [ "${attempt}" -lt "${MAX_ATTEMPTS}" ]; then
        echo "Waiting ${SLEEP_INTERVAL}s before retry..."
        sleep "${SLEEP_INTERVAL}"
    fi
    attempt=$((attempt + 1))
done

echo "=========================================================="
echo " [CRITICAL] Health check FAILED after ${MAX_ATTEMPTS} attempts."
echo "=========================================================="
exit 1
