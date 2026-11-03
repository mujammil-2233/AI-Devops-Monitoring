#!/usr/bin/env bash
# ==============================================================================
# Enterprise Auto-Healing Circuit Breaker Engine
# Detects unhealthy/stopped containers, applies rate-limited auto-recovery,
# prevents crash loops, logs telemetry, and alerts on critical escalation.
#
# SAFETY NOTICE:
# Strictly restricted to Docker container management.
# NEVER restarts host EC2 instance or touches host system services.
#
# Author: DevOps Engineering Team
# Project: AI-Powered DevOps Monitoring & Auto-Healing System
# ==============================================================================

set -euo pipefail

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
CONTAINER_NAME="${CONTAINER_NAME:-flask-app}"
HEALTH_URL="${HEALTH_URL:-http://localhost:5000/health}"
LOG_DIR="${LOG_DIR:-logs}"
REPORT_DIR="${REPORT_DIR:-reports}"
HEALING_LOG="${LOG_DIR}/healing.log"
STATE_FILE="${LOG_DIR}/healing_state.json"
REPORT_FILE="${REPORT_DIR}/healing_report.json"

MAX_RETRIES="${MAX_RETRY_LIMIT:-3}"
COOLDOWN_SECONDS="${COOLDOWN_SECONDS:-20}"
CIRCUIT_RESET_WINDOW="${CIRCUIT_RESET_WINDOW:-300}"  # 5 minutes
CHECK_INTERVAL="${CHECK_INTERVAL:-15}"

# Create required directories
mkdir -p "${LOG_DIR}" "${REPORT_DIR}"

log_msg() {
    local level="$1"
    local message="$2"
    local timestamp
    timestamp="$(date -u +"%Y-%m-%d %H:%M:%S UTC")"
    echo "${timestamp} [${level}] [AutoHealer] ${message}" | tee -a "${HEALING_LOG}"
}

# ---------------------------------------------------------
# State Management & Circuit Breaker Logic
# ---------------------------------------------------------
get_state_var() {
    local key="$1"
    local default_val="$2"
    if [ -f "${STATE_FILE}" ]; then
        # Simple extraction without requiring jq
        local val
        val=$(grep -o "\"${key}\":[^,}]*" "${STATE_FILE}" | head -1 | cut -d':' -f2 | tr -d ' "')
        if [ -n "${val}" ]; then
            echo "${val}"
            return
        fi
    fi
    echo "${default_val}"
}

update_state() {
    local restart_count="$1"
    local last_restart_time="$2"
    local circuit_status="$3"
    cat <<EOF > "${STATE_FILE}"
{
  "container_name": "${CONTAINER_NAME}",
  "restart_count": ${restart_count},
  "last_restart_time": ${last_restart_time},
  "circuit_status": "${circuit_status}",
  "updated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
}

# Initialize state if not present
if [ ! -f "${STATE_FILE}" ]; then
    update_state 0 0 "CLOSED"
fi

# ---------------------------------------------------------
# Container Inspection & Health Probing
# ---------------------------------------------------------
check_container_health() {
    # 1. Check if Docker is available
    if ! command -v docker >/dev/null 2>&1; then
        log_msg "ERROR" "Docker CLI not found on host."
        return 2
    fi

    # 2. Check if container exists
    local container_id
    container_id=$(docker ps -aq -f "name=^/${CONTAINER_NAME}$")
    if [ -z "${container_id}" ]; then
        log_msg "WARNING" "Container '${CONTAINER_NAME}' does not exist."
        return 1
    fi

    # 3. Check container runtime status
    local container_status
    container_status=$(docker inspect --format '{{.State.Status}}' "${CONTAINER_NAME}" 2>/dev/null || echo "unknown")

    if [ "${container_status}" != "running" ]; then
        log_msg "WARNING" "Container '${CONTAINER_NAME}' is in state: ${container_status} (Not running)."
        return 1
    fi

    # 4. Check Docker Healthcheck state if available
    local docker_health
    docker_health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "${CONTAINER_NAME}" 2>/dev/null || echo "none")
    if [ "${docker_health}" = "unhealthy" ]; then
        log_msg "WARNING" "Docker internal health check reports UNHEALTHY for '${CONTAINER_NAME}'."
        return 1
    fi

    # 5. Direct HTTP health probe
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 4 --max-time 6 "${HEALTH_URL}" 2>/dev/null || true)
    if [ -z "${http_code}" ]; then
        http_code="000"
    fi
    if [ "${http_code}" != "200" ]; then
        log_msg "WARNING" "HTTP Health probe to ${HEALTH_URL} returned status code: ${http_code} (Expected 200)."
        return 1
    fi

    return 0
}

# ---------------------------------------------------------
# Healing Action Execution
# ---------------------------------------------------------
perform_healing() {
    local now
    now=$(date +%s)
    local restart_count
    restart_count=$(get_state_var "restart_count" 0)
    local last_restart_time
    last_restart_time=$(get_state_var "last_restart_time" 0)
    local circuit_status
    circuit_status=$(get_state_var "circuit_status" "CLOSED")

    # Check if reset window has passed to reset retry counter
    local time_since_last=$((now - last_restart_time))
    if [ "${time_since_last}" -gt "${CIRCUIT_RESET_WINDOW}" ] && [ "${restart_count}" -gt 0 ]; then
        log_msg "INFO" "Reset window (${CIRCUIT_RESET_WINDOW}s) elapsed. Resetting restart counter from ${restart_count} to 0."
        restart_count=0
        circuit_status="CLOSED"
        update_state 0 "${now}" "CLOSED"
    fi

    # Check if Circuit Breaker is tripped
    if [ "${restart_count}" -ge "${MAX_RETRIES}" ]; then
        log_msg "CRITICAL" "=========================================================="
        log_msg "CRITICAL" "[CIRCUIT BREAKER TRIPPED] Maximum restart attempts (${MAX_RETRIES}) reached!"
        log_msg "CRITICAL" "Preventing crash-loop storm. Automatic healing HALTED for '${CONTAINER_NAME}'."
        log_msg "CRITICAL" "Escalating incident to on-call engineer / AI Log Analyzer."
        log_msg "CRITICAL" "=========================================================="
        update_state "${restart_count}" "${now}" "OPEN"

        # Generate escalation report
        cat <<EOF > "${REPORT_FILE}"
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "status": "CIRCUIT_BREAKER_OPEN",
  "container": "${CONTAINER_NAME}",
  "reason": "Container failed repeatedly after ${MAX_RETRIES} automatic restart attempts.",
  "action_taken": "Automated restarts suspended to prevent resource starvation.",
  "recommended_action": "Check application error logs via AI Log Analyzer (reports/latest_report.md) or inspect container logs."
}
EOF
        return 1
    fi

    # Check cooldown period
    if [ "${time_since_last}" -lt "${COOLDOWN_SECONDS}" ] && [ "${last_restart_time}" -gt 0 ]; then
        local remaining=$((COOLDOWN_SECONDS - time_since_last))
        log_msg "INFO" "In cooldown window. Waiting ${remaining}s before attempting restart..."
        return 0
    fi

    # Increment restart count
    restart_count=$((restart_count + 1))
    log_msg "NOTICE" "Initiating container recovery for '${CONTAINER_NAME}' (Attempt ${restart_count}/${MAX_RETRIES})..."

    # Execute container restart safely
    if docker restart --time 10 "${CONTAINER_NAME}" >/dev/null 2>&1; then
        log_msg "SUCCESS" "Container '${CONTAINER_NAME}' restarted successfully."
        update_state "${restart_count}" "${now}" "HALF_OPEN"

        # Generate recovery report
        cat <<EOF > "${REPORT_FILE}"
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "status": "HEALED",
  "container": "${CONTAINER_NAME}",
  "attempt": ${restart_count},
  "max_retries": ${MAX_RETRIES},
  "action_taken": "Graceful docker container restart executed."
}
EOF
    else
        log_msg "ERROR" "Failed to restart Docker container '${CONTAINER_NAME}'."
        update_state "${restart_count}" "${now}" "ERROR"
    fi
}

# ---------------------------------------------------------
# Run Mode Execution
# ---------------------------------------------------------
run_once() {
    log_msg "INFO" "Executing single health verification probe for '${CONTAINER_NAME}'..."
    if check_container_health; then
        log_msg "INFO" "Container '${CONTAINER_NAME}' is HEALTHY."
        return 0
    else
        log_msg "WARNING" "Container '${CONTAINER_NAME}' is UNHEALTHY! Triggering healing engine..."
        perform_healing
        return 0
    fi
}

run_daemon() {
    log_msg "INFO" "=========================================================="
    log_msg "INFO" " Starting Auto-Healing Daemon Service"
    log_msg " Monitored Container : ${CONTAINER_NAME}"
    log_msg " Probe Endpoint      : ${HEALTH_URL}"
    log_msg " Max Retries         : ${MAX_RETRIES}"
    log_msg " Cooldown Window     : ${COOLDOWN_SECONDS}s"
    log_msg " Reset Window        : ${CIRCUIT_RESET_WINDOW}s"
    log_msg " Poll Interval       : ${CHECK_INTERVAL}s"
    log_msg "=========================================================="

    while true; do
        if ! check_container_health; then
            perform_healing
        fi
        sleep "${CHECK_INTERVAL}"
    done
}

# Argument dispatch
case "${1:-}" in
    --once)
        run_once
        ;;
    --daemon)
        run_daemon
        ;;
    --status)
        echo "Current Healing State:"
        cat "${STATE_FILE}" 2>/dev/null || echo "No state file found."
        ;;
    *)
        echo "Usage: $0 {--once|--daemon|--status}"
        exit 1
        ;;
esac
