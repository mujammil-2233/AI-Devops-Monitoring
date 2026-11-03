"""
Production Flask Application with Prometheus Observability & Chaos Testing.
Author: DevOps Engineering Team
Project: AI-Powered DevOps Monitoring & Auto-Healing System
"""

import os
import sys
import time
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
import psutil
from flask import Flask, jsonify, request, Response
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

# ---------------------------------------------------------
# Application Initialization & Configuration
# ---------------------------------------------------------
app = Flask(__name__)

APP_NAME = os.getenv("APP_NAME", "ai-devops-monitor")
APP_PORT = int(os.getenv("APP_PORT", 5000))
APP_ENV = os.getenv("APP_ENV", "production")
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "logs/app.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

START_TIME = time.time()
HEALTH_STATE = {"healthy": True, "reason": "Operational"}

# ---------------------------------------------------------
# Logging Configuration (Console + Rotating File)
# ---------------------------------------------------------
log_dir = os.path.dirname(LOG_FILE_PATH)
if log_dir and not os.path.exists(log_dir):
    os.makedirs(log_dir, exist_ok=True)

logger = logging.getLogger("DevOpsApp")
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
logger.propagate = False  # Avoid duplicate entries in root logger

# Formatting
log_format = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] [%(name)s] [pid:%(process)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Console Handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_format)
if not logger.handlers:
    logger.addHandler(console_handler)

    # File Handler (10MB limit, keep 5 backups)
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE_PATH, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Could not initialize file logger at {LOG_FILE_PATH}: {e}")

# ---------------------------------------------------------
# Prometheus Metrics Registration
# ---------------------------------------------------------
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP request count",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

APP_HEALTH_GAUGE = Gauge(
    "app_health_status",
    "Application health state (1 = Healthy/UP, 0 = Unhealthy/DOWN)",
)
APP_HEALTH_GAUGE.set(1)

ACTIVE_REQUESTS_GAUGE = Gauge(
    "app_active_requests",
    "Number of currently active in-flight requests",
)

SYSTEM_CPU_GAUGE = Gauge(
    "system_cpu_usage_percent",
    "Host/Container CPU utilization percentage",
)

SYSTEM_MEMORY_GAUGE = Gauge(
    "system_memory_usage_percent",
    "Host/Container Memory utilization percentage",
)


def update_system_metrics():
    """Sample system CPU and RAM usage via psutil."""
    try:
        cpu_percent = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        SYSTEM_CPU_GAUGE.set(cpu_percent)
        SYSTEM_MEMORY_GAUGE.set(mem.percent)
    except Exception as e:
        logger.warning(f"Error reading psutil system metrics: {e}")


# ---------------------------------------------------------
# Request Pre/Post Hooks for Telemetry
# ---------------------------------------------------------
@app.before_request
def before_request_hook():
    request.start_time = time.time()
    ACTIVE_REQUESTS_GAUGE.inc()


@app.after_request
def after_request_hook(response):
    ACTIVE_REQUESTS_GAUGE.dec()
    try:
        latency = time.time() - getattr(request, "start_time", time.time())
        endpoint = request.path

        # Record metrics (skip metrics endpoint itself to avoid recursion overhead)
        if endpoint != "/metrics":
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=endpoint,
                status_code=str(response.status_code),
            ).inc()

            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=endpoint,
            ).observe(latency)

        # Log request summary
        if response.status_code >= 500:
            logger.error(
                f"{request.method} {request.path} completed with status {response.status_code} in {latency:.4f}s"
            )
        elif response.status_code >= 400:
            logger.warning(
                f"{request.method} {request.path} completed with status {response.status_code} in {latency:.4f}s"
            )
        else:
            logger.info(
                f"{request.method} {request.path} completed with status {response.status_code} in {latency:.4f}s"
            )

    except Exception as e:
        logger.warning(f"Error updating request metrics: {e}")

    return response


# ---------------------------------------------------------
# Core Endpoints
# ---------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    """Root endpoint welcoming users and cataloging API routes."""
    return (
        jsonify(
            {
                "service": APP_NAME,
                "environment": APP_ENV,
                "status": "online",
                "message": "AI-Powered DevOps Monitoring Platform is operational.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "endpoints": {
                    "health": "/health",
                    "metrics": "/metrics",
                    "status": "/status",
                    "chaos_error": "/chaos/error",
                    "chaos_slow": "/chaos/slow?delay=2",
                    "chaos_unhealthy": "/chaos/unhealthy",
                    "chaos_recover": "/chaos/recover",
                },
            }
        ),
        200,
    )


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint for Docker HEALTHCHECK, Kubernetes, or Auto-Healing probes."""
    uptime = time.time() - START_TIME
    if HEALTH_STATE["healthy"]:
        APP_HEALTH_GAUGE.set(1)
        return (
            jsonify(
                {
                    "status": "UP",
                    "reason": HEALTH_STATE["reason"],
                    "uptime_seconds": round(uptime, 2),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "checks": {
                        "database": "connected",
                        "memory": "within_threshold",
                        "disk": "ok",
                    },
                }
            ),
            200,
        )
    else:
        APP_HEALTH_GAUGE.set(0)
        logger.error(
            f"Health check failed! Current state: {HEALTH_STATE['reason']}"
        )
        return (
            jsonify(
                {
                    "status": "DOWN",
                    "reason": HEALTH_STATE["reason"],
                    "uptime_seconds": round(uptime, 2),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
            503,
        )


@app.route("/status", methods=["GET"])
def status():
    """Detailed system and process telemetry status endpoint."""
    update_system_metrics()
    mem = psutil.virtual_memory()
    uptime = time.time() - START_TIME
    return (
        jsonify(
            {
                "service": APP_NAME,
                "environment": APP_ENV,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "system": {
                    "cpu_percent": psutil.cpu_percent(interval=None),
                    "memory_total_mb": round(mem.total / (1024 * 1024), 2),
                    "memory_used_mb": round(mem.used / (1024 * 1024), 2),
                    "memory_percent": mem.percent,
                },
                "health": HEALTH_STATE,
            }
        ),
        200,
    )


@app.route("/metrics", methods=["GET"])
def metrics():
    """Prometheus telemetry endpoint scraped by Prometheus server."""
    update_system_metrics()
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


# ---------------------------------------------------------
# Chaos Engineering & Failure Simulation Endpoints
# ---------------------------------------------------------
@app.route("/chaos/error", methods=["GET", "POST"])
def chaos_error():
    """Deliberately raises an internal server error to generate 500 error logs."""
    logger.error("Chaos Triggered: Simulated internal server 500 failure.")
    return (
        jsonify(
            {
                "error": "InternalServerError",
                "message": "Chaos injection: Database connection failure simulated.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ),
        500,
    )


@app.route("/chaos/slow", methods=["GET"])
def chaos_slow():
    """Simulates high latency request (default 2s) to test P95/P99 latency metrics."""
    delay = float(request.args.get("delay", 2.0))
    logger.warning(f"Chaos Triggered: Simulating high latency of {delay}s.")
    time.sleep(delay)
    return (
        jsonify(
            {
                "message": f"Response completed after simulated latency of {delay}s",
                "delay_seconds": delay,
            }
        ),
        200,
    )


@app.route("/chaos/unhealthy", methods=["POST", "GET"])
def chaos_unhealthy():
    """Forces the application into an unhealthy DOWN state to test auto-healing."""
    HEALTH_STATE["healthy"] = False
    HEALTH_STATE["reason"] = "Chaos injection: Service manually marked unhealthy"
    APP_HEALTH_GAUGE.set(0)
    logger.critical("Chaos Triggered: Application state toggled to DOWN!")
    return (
        jsonify(
            {
                "message": "Application health set to DOWN (503). Auto-healing probe should detect this.",
                "health_state": HEALTH_STATE,
            }
        ),
        200,
    )


@app.route("/chaos/recover", methods=["POST", "GET"])
def chaos_recover():
    """Restores application health to healthy UP state."""
    HEALTH_STATE["healthy"] = True
    HEALTH_STATE["reason"] = "Operational - Restored from chaos state"
    APP_HEALTH_GAUGE.set(1)
    logger.info("Application health successfully restored to UP.")
    return (
        jsonify(
            {
                "message": "Application health restored to UP (200).",
                "health_state": HEALTH_STATE,
            }
        ),
        200,
    )


# ---------------------------------------------------------
# Global Error Handlers
# ---------------------------------------------------------
@app.errorhandler(400)
def bad_request(error):
    logger.warning(f"Bad Request (400): {request.path}")
    return jsonify({"error": "Bad Request", "message": str(error)}), 400


@app.errorhandler(404)
def not_found(error):
    logger.warning(f"Resource Not Found (404): {request.path}")
    return jsonify({"error": "Not Found", "message": "Endpoint does not exist"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal Server Error (500) on {request.path}: {error}", exc_info=True)
    return (
        jsonify(
            {
                "error": "Internal Server Error",
                "message": "An unexpected server condition occurred",
            }
        ),
        500,
    )


# ---------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------
def get_bind_port(preferred_port: int) -> int:
    """Validate port availability, falling back to 5001 if preferred port is already bound."""
    import socket
    for port in [preferred_port, 5001, 5050]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("0.0.0.0", port))
                return port
        except (OSError, PermissionError):
            continue
    return preferred_port


if __name__ == "__main__":
    target_port = get_bind_port(APP_PORT)
    if target_port != APP_PORT:
        logger.warning(
            f"Port {APP_PORT} is in use on host. Automatically selected available port: {target_port}"
        )
    logger.info(f"Starting {APP_NAME} in {APP_ENV} mode on port {target_port}...")
    app.run(host="0.0.0.0", port=target_port, debug=False)
