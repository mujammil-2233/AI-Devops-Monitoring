
#!/bin/bash

set -u

CONTAINER_NAME="${CONTAINER_NAME:-ai-devops-app}"
HEALTH_URL="${HEALTH_URL:-http://localhost:5000/health}"
CHECK_INTERVAL="${CHECK_INTERVAL:-15}"
MAX_RETRIES="${MAX_RETRIES:-3}"
LOG_DIR="${LOG_DIR:-logs}"
HEALING_LOG="${LOG_DIR}/healing.log"

mkdir -p "$LOG_DIR"

log_msg() {
    local level="${1:-INFO}"
    local message="${2:-}"

    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') [$level] [AutoHealer] $message" | tee -a "$HEALING_LOG"
}

check_health() {
    docker inspect -f '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null | grep -q true || return 1

    curl -fsS --max-time 5 "$HEALTH_URL" >/dev/null 2>&1
}

heal_container() {
    local attempt=1

    while [ "$attempt" -le "$MAX_RETRIES" ]; do
        log_msg WARN "Healing attempt $attempt/$MAX_RETRIES"

        if docker restart --timeout 10 "$CONTAINER_NAME"; then
            sleep 5

            if check_health; then
                log_msg INFO "Auto-healing successful."
                return 0
            fi
        fi

        log_msg ERROR "Healing attempt $attempt failed."
        attempt=$((attempt + 1))
        sleep 5
    done

    log_msg ERROR "Auto-healing failed after maximum retries."
    return 1
}

run_once() {
    log_msg INFO "Executing health verification for $CONTAINER_NAME."

    if check_health; then
        log_msg INFO "Container $CONTAINER_NAME is HEALTHY."
    else
        log_msg WARN "Container $CONTAINER_NAME is UNHEALTHY."
        heal_container
    fi
}

run_daemon() {
    log_msg INFO "Starting Auto-Healing Daemon Service"

    while true; do
        run_once
        sleep "$CHECK_INTERVAL"
    done
}

case "${1:-}" in
    --once)
        run_once
        ;;
    --daemon)
        run_daemon
        ;;
    --status)
        if check_health; then
            echo "Container HEALTHY"
        else
            echo "Container UNHEALTHY"
        fi
        ;;
    *)
        echo "Usage: $0 {--once|--daemon|--status}"
        exit 1
        ;;
esac
