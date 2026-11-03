"""
Unit and Integration Test Suite for AI-Powered DevOps Monitoring Platform.
Covers:
  - Flask endpoints (/, /health, /status, /metrics, /chaos/*)
  - Global error handling
  - AI Log Analyzer (Parsing, Sanitization, Anomaly Detection, Report Gen)
  - Auto-Healing Circuit Breaker Algorithm & State Management

Author: DevOps Engineering Team
"""

import os
import sys
import json
import time
import pytest

# Ensure app and ai-analyzer modules are in python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT_DIR, "app"))
sys.path.insert(0, os.path.join(ROOT_DIR, "ai-analyzer"))

from app import app as flask_app
from analyzer import LogSanitizer, LogParser, RuleBasedExpertEngine, AILogAnalyzer


@pytest.fixture
def client():
    """Flask test client fixture."""
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client


# =========================================================
# 1. Flask Application Endpoints Tests
# =========================================================

def test_home_endpoint(client):
    """Test that the index endpoint returns HTTP 200 and service metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.get_json()
    assert "service" in data
    assert data["status"] == "online"
    assert "endpoints" in data
    assert data["endpoints"]["health"] == "/health"
    assert data["endpoints"]["metrics"] == "/metrics"


def test_health_endpoint_healthy(client):
    """Test that default health state returns HTTP 200 and status UP."""
    # Ensure health is UP first
    client.post("/chaos/recover")
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "UP"
    assert "uptime_seconds" in data
    assert data["checks"]["database"] == "connected"


def test_health_endpoint_unhealthy_and_recovery(client):
    """Test chaos injection setting health to DOWN (503) and recovery to UP (200)."""
    # Force unhealthy
    unhealthy_resp = client.post("/chaos/unhealthy")
    assert unhealthy_resp.status_code == 200

    probe_resp = client.get("/health")
    assert probe_resp.status_code == 503
    probe_data = probe_resp.get_json()
    assert probe_data["status"] == "DOWN"

    # Recover health
    recover_resp = client.post("/chaos/recover")
    assert recover_resp.status_code == 200

    recovered_probe = client.get("/health")
    assert recovered_probe.status_code == 200
    assert recovered_probe.get_json()["status"] == "UP"


def test_status_endpoint(client):
    """Test that the /status endpoint provides detailed telemetry."""
    response = client.get("/status")
    assert response.status_code == 200
    data = response.get_json()
    assert "system" in data
    assert "memory_percent" in data["system"]
    assert "uptime_seconds" in data


def test_metrics_endpoint(client):
    """Test that the /metrics endpoint outputs valid Prometheus metrics format."""
    # Generate a few requests to populate counters
    client.get("/")
    client.get("/health")

    response = client.get("/metrics")
    assert response.status_code == 200
    content = response.data.decode("utf-8")
    assert "http_requests_total" in content
    assert "app_health_status" in content
    assert "system_cpu_usage_percent" in content


def test_chaos_error_endpoint(client):
    """Test that /chaos/error triggers an HTTP 500 response."""
    response = client.get("/chaos/error")
    assert response.status_code == 500
    data = response.get_json()
    assert data["error"] == "InternalServerError"


def test_not_found_handler(client):
    """Test 404 JSON error handler for undefined routes."""
    response = client.get("/non-existent-endpoint-xyz")
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "Not Found"


# =========================================================
# 2. AI Log Analyzer Tests
# =========================================================

def test_log_sanitizer():
    """Verify that credentials, tokens, AWS keys, and IPs are redacted."""
    sensitive_log = (
        'User auth failed: Bearer eyJhbGciOiJIUzI1Ni.secret_payload '
        'AccessKey: AKIAIOSFODNN7EXAMPLE password="supersecret123" host: 198.51.100.42'
    )
    sanitized = LogSanitizer.sanitize(sensitive_log)
    assert "[REDACTED_TOKEN]" in sanitized
    assert "[REDACTED_AWS_KEY]" in sanitized
    assert '"[REDACTED]"' in sanitized
    assert "[REDACTED_IP]" in sanitized
    assert "supersecret123" not in sanitized
    assert "AKIAIOSFODNN7EXAMPLE" not in sanitized


def test_log_parser():
    """Verify that structured log lines are accurately parsed."""
    line = "2026-11-03 16:40:54 [ERROR] [DevOpsApp] [pid:1234] Database connection refused on port 5432"
    parsed = LogParser.parse_line(line)
    assert parsed is not None
    assert parsed["timestamp"] == "2026-11-03 16:40:54"
    assert parsed["level"] == "ERROR"
    assert parsed["logger"] == "DevOpsApp"
    assert parsed["pid"] == "1234"
    assert "Database connection refused" in parsed["message"]


def test_rule_based_expert_engine():
    """Test that failure signatures correctly map to root causes and remediations."""
    entries = [
        {
            "timestamp": "2026-11-03 16:40:54",
            "level": "ERROR",
            "logger": "DevOpsApp",
            "message": "database connection failure to host postgresql.internal",
            "raw": "...",
        },
        {
            "timestamp": "2026-11-03 16:40:55",
            "level": "CRITICAL",
            "logger": "DevOpsApp",
            "message": "MemoryError: Out of Memory while allocating buffer",
            "raw": "...",
        },
    ]

    findings = RuleBasedExpertEngine.analyze(entries)
    categories = [f["category"] for f in findings]
    assert "DatabaseConnectivityFailure" in categories
    assert "MemoryExhaustion" in categories

    # Verify remediation list is populated
    db_finding = next(f for f in findings if f["category"] == "DatabaseConnectivityFailure")
    assert len(db_finding["remediation"]) > 0
    assert any("database" in r.lower() for r in db_finding["remediation"])


def test_ai_analyzer_report_generation(tmp_path):
    """Test full analysis run and report writing in temporary test directory."""
    test_log = tmp_path / "test_app.log"
    reports_dir = tmp_path / "reports"

    # Write sample synthetic log entries
    test_log.write_text(
        "2026-11-03 12:00:00 [INFO] [DevOpsApp] Application startup completed\n"
        "2026-11-03 12:01:00 [WARNING] [DevOpsApp] Simulating high latency of 2.5s\n"
        "2026-11-03 12:02:00 [ERROR] [DevOpsApp] Chaos Triggered: Simulated internal server 500 failure.\n"
        "2026-11-03 12:02:05 [CRITICAL] [DevOpsApp] Chaos Triggered: Application state toggled to DOWN!\n"
    )

    analyzer = AILogAnalyzer(
        log_file=str(test_log),
        output_dir=str(reports_dir),
        gemini_api_key=None,  # Baseline mode
    )

    report = analyzer.analyze()
    assert report["status"] == "INCIDENT_DETECTED"
    assert report["summary"]["error_count"] == 1
    assert report["summary"]["critical_count"] == 1
    assert report["summary"]["warning_count"] == 1
    assert report["summary"]["info_count"] == 1

    # Verify report files were generated
    latest_json = reports_dir / "latest_report.json"
    latest_md = reports_dir / "latest_report.md"
    assert latest_json.exists()
    assert latest_md.exists()

    with open(latest_json) as f:
        data = json.load(f)
        assert data["incident_id"].startswith("INC-")


# =========================================================
# 3. Auto-Healing Circuit Breaker Unit Tests
# =========================================================

class CircuitBreakerSimulator:
    """Pure-logic simulator matching scripts/auto-healing.sh behavior."""

    def __init__(self, max_retries=3, cooldown_seconds=20, reset_window=300):
        self.max_retries = max_retries
        self.cooldown_seconds = cooldown_seconds
        self.reset_window = reset_window
        self.restart_count = 0
        self.last_restart_time = 0
        self.circuit_status = "CLOSED"

    def attempt_recovery(self, current_time: int) -> str:
        # Check reset window
        if (current_time - self.last_restart_time) > self.reset_window and self.restart_count > 0:
            self.restart_count = 0
            self.circuit_status = "CLOSED"

        # Check circuit breaker limit
        if self.restart_count >= self.max_retries:
            self.circuit_status = "OPEN"
            return "CIRCUIT_BREAKER_TRIPPED"

        # Check cooldown
        if (current_time - self.last_restart_time) < self.cooldown_seconds and self.last_restart_time > 0:
            return "COOLDOWN_ACTIVE"

        # Execute restart
        self.restart_count += 1
        self.last_restart_time = current_time
        self.circuit_status = "HALF_OPEN"
        return "RESTARTED"


def test_circuit_breaker_prevents_infinite_loops():
    """Verify that circuit breaker stops restarting after MAX_RETRIES to prevent crash loops."""
    breaker = CircuitBreakerSimulator(max_retries=3, cooldown_seconds=10, reset_window=100)

    # 1st restart at t=10
    action = breaker.attempt_recovery(current_time=10)
    assert action == "RESTARTED"
    assert breaker.restart_count == 1

    # Immediate next attempt at t=15 should hit cooldown (15-10 < 10)
    action = breaker.attempt_recovery(current_time=15)
    assert action == "COOLDOWN_ACTIVE"
    assert breaker.restart_count == 1

    # 2nd restart at t=25 (cooldown expired)
    action = breaker.attempt_recovery(current_time=25)
    assert action == "RESTARTED"
    assert breaker.restart_count == 2

    # 3rd restart at t=40
    action = breaker.attempt_recovery(current_time=40)
    assert action == "RESTARTED"
    assert breaker.restart_count == 3

    # 4th attempt at t=60: Max retries (3) reached! Circuit breaker MUST trip!
    action = breaker.attempt_recovery(current_time=60)
    assert action == "CIRCUIT_BREAKER_TRIPPED"
    assert breaker.circuit_status == "OPEN"

    # Reset window passes at t=200 (> 40 + 100)
    action = breaker.attempt_recovery(current_time=200)
    assert action == "RESTARTED"
    assert breaker.restart_count == 1
    assert breaker.circuit_status == "HALF_OPEN"
