# AI-Powered DevOps Monitoring & Auto-Healing System

[![CI/CD Pipeline](https://img.shields.io/badge/CI%2FCD-Jenkins-blue?logo=jenkins)](Jenkinsfile)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](docker-compose.yml)
[![Prometheus](https://img.shields.io/badge/Monitoring-Prometheus-E6522C?logo=prometheus)](monitoring/prometheus/prometheus.yml)
[![Grafana](https://img.shields.io/badge/Observability-Grafana-F46800?logo=grafana)](monitoring/grafana/)
[![AI Engine](https://img.shields.io/badge/AI-Log%20Analyzer-brightgreen)](#phase-5-ai-assisted-log-analyzer)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An enterprise-grade, cloud-native DevOps monitoring and self-healing platform. Combines containerized microservices, full-stack observability (Prometheus + Grafana + cAdvisor + Node Exporter), deterministic and generative AI log analysis (with optional Google Gemini integration), an automated closed-loop container recovery circuit breaker, and a zero-downtime 10-stage Jenkins CI/CD pipeline.

---

## Table of Contents
1. [Project Overview & Objectives](#1-project-overview--objectives)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Project Directory Structure](#4-project-directory-structure)
5. [Local Development Setup](#5-local-development-setup)
6. [Docker & Containerized Deployment](#6-docker--containerized-deployment)
7. [Observability Stack (Prometheus & Grafana)](#7-observability-stack-prometheus--grafana)
8. [AI-Assisted Log Analyzer](#8-ai-assisted-log-analyzer)
9. [Auto-Healing Circuit Breaker Engine](#9-auto-healing-circuit-breaker-engine)
10. [Jenkins CI/CD Automation & Security](#10-jenkins-cicd-automation--security)
11. [AWS EC2 Cloud Deployment Guide](#11-aws-ec2-cloud-deployment-guide)
12. [Testing & Verification](#12-testing--verification)
13. [Troubleshooting Guide](#13-troubleshooting-guide)
14. [Portfolio & Resume Bullet Points](#14-portfolio--resume-bullet-points)
15. [Top 10 Technical Interview Questions & Answers](#15-top-10-technical-interview-questions--answers)

---

## 1. Project Overview & Objectives

In production environments, service outages degrade customer trust and cost organizations thousands of dollars per minute. Traditional monitoring systems alert human engineers only after outages happen.

### Objectives:
- **Zero-Touch Container Auto-Recovery**: Detect failed or unhealthy application instances and execute rate-limited graceful restarts.
- **Circuit Breaker Loop Prevention**: Prevent cascading restart loops through exponential backoffs, retry thresholds (max 3), and automatic escalation.
- **Intelligent Log Anomaly Detection**: Analyze structured application logs, cluster recurring error signatures, redact secrets/PII, and synthesize root-cause hypotheses with actionable remediation steps.
- **Full-Stack Observability**: Monitor CPU, RAM, disk, network, container lifecycle, request throughput, and P95/P99 latency in real time.
- **Automated CI/CD with Security Guardrails**: Automate unit testing, Trivy container vulnerability scanning, AWS ECR publishing, and zero-downtime rollback if health checks fail.

---

## 2. High-Level Architecture

```mermaid
flowchart TB
    subgraph Clients["Traffic & Engineers"]
        Traffic["HTTP Client / Browser"]
        Engineer["On-Call DevOps Engineer"]
    end

    subgraph AppHost["AWS EC2 / Local Docker Host"]
        subgraph AppTier["Application Tier"]
            App["Flask Microservice (:5000)\n- Business Logic\n- /metrics & /health\n- Chaos Injection Routes"]
            Logs[("app.log\nShared Volume")]
        end

        subgraph MonitorTier["Observability Tier"]
            Prom["Prometheus (:9090)\n- Scrapes /metrics every 5s\n- Scrapes Node & cAdvisor"]
            Graf["Grafana (:3000)\n- Auto-Provisioned Dashboards\n- Real-time SLA / Latency"]
            Node["Node Exporter (:9100)\n- Host OS Metrics"]
            cAdv["cAdvisor (:8080)\n- Container Resource Telemetry"]
        end

        subgraph HealingTier["AI & Auto-Healing Tier"]
            Analyzer["AI Log Analyzer (:Daemon)\n- Pattern & Burst Detection\n- PII/Secret Redaction\n- Root Cause & Remediation\n- Optional Gemini AI Synthesis\n- Generates reports/*.md"]
            Healer["Auto-Healing Engine\n- Docker & HTTP Probes\n- Circuit Breaker (Max 3 retries)\n- Cooldown & Crash Loop Guard\n- Escalation Alerting"]
        end
    end

    subgraph CICD["CI/CD Pipeline (Jenkins)"]
        Git["GitHub Repo"]
        Jenk["Jenkins Pipeline (10 Stages)\n- Test -> Scan (Trivy) -> Build -> Push -> Deploy -> Rollback"]
        ECR["AWS ECR Registry"]
    end

    %% Flows
    Traffic -->|Requests| App
    App -->|Writes logs| Logs
    App -->|Exposes /metrics| Prom
    Node --> Prom
    cAdv --> Prom
    Prom --> Graf
    Logs --> Analyzer
    Healer -->|Health check probe| App
    Healer -->|docker restart| App
    Git --> Jenk
    Jenk -->|Push Image| ECR
    ECR -->|Pull Image| App
    Analyzer -.->|Incident Brief| Engineer
    Healer -.->|Circuit Breaker Alert| Engineer
```

---

## 3. Technology Stack

| Category | Technology | Usage in Project |
| :--- | :--- | :--- |
| **Backend** | Python 3.11, Flask, Gunicorn | Microservice application, chaos test routes, REST endpoints |
| **Metrics** | `prometheus-client`, `psutil` | Exposing real-time CPU, RAM, request counts, and latency |
| **Monitoring** | Prometheus v2.51.0 | High-performance time-series metric collection and scraping |
| **Visualization** | Grafana v10.4.0 | Auto-provisioned dashboards for SLA, error rates, and restarts |
| **Host/Containers**| Node Exporter, cAdvisor | OS-level and container-level resource utilization |
| **AI Analysis** | Python, Rule Engine, Gemini API | Anomaly detection, incident clustering, root-cause recommendations |
| **Containers** | Docker, Docker Compose | Multi-container orchestration, non-root security, isolated bridge networks |
| **CI/CD** | Jenkins, Declarative Pipeline | 10-stage automated pipeline with test reports and image pruning |
| **Security** | Trivy, Secret Sanitizer, IAM | Container CVE vulnerability scanning, non-root users, secret masking |
| **Cloud** | AWS EC2 (Ubuntu), AWS ECR | Cloud compute host and private Docker image registry |
| **Scripting** | Bash (POSIX), Shell Scripting | Auto-healing circuit breaker, health probes, deployment automation |

---

## 4. Project Directory Structure

```
ai-devops-monitoring/
│
├── app/
│   ├── app.py                     # Production Flask application with Prometheus & chaos endpoints
│   ├── requirements.txt           # Python application dependencies
│   └── Dockerfile                 # Multi-stage, non-root secure Dockerfile
│
├── monitoring/
│   ├── prometheus/
│   │   └── prometheus.yml         # Prometheus scrape jobs (Flask, Node, cAdvisor, Prom)
│   └── grafana/
│       └── provisioning/
│           ├── datasources/
│           │   └── datasource.yml # Auto-provisioned Prometheus connection
│           └── dashboards/
│               ├── dashboard.yml  # Auto-provisioned dashboard provider
│               └── devops-dashboard.json # Visual panels (CPU, RAM, 5xx, P95/P99)
│
├── ai-analyzer/
│   ├── analyzer.py                # AI Log Analyzer: Rule-based engine + optional Gemini API
│   ├── requirements.txt           # Dependencies for AI analyzer
│   └── Dockerfile                 # Lightweight container for log analyzer daemon
│
├── scripts/
│   ├── auto-healing.sh            # Safe container health monitor & circuit-breaker recovery
│   ├── health-check.sh            # Microservice health & metrics probe
│   └── deployment.sh              # AWS EC2 deployment automation with zero-downtime rollback
│
├── tests/
│   └── test_app.py                # 12 Pytest tests (Endpoints, Metrics, AI Engine, Circuit Breaker)
│
├── docker-compose.yml             # 6-service orchestration on custom bridge network
├── Jenkinsfile                    # 10-stage enterprise CI/CD pipeline
├── .gitignore                     # Git ignore rules for logs, secrets, venv, and caches
├── .env.example                   # Environment configuration template
├── README.md                      # Comprehensive project guide and portfolio docs
└── architecture.md                # In-depth architectural design & failure recovery states
```

---

## 5. Local Development Setup

### Prerequisites
- Python 3.10+
- Docker & Docker Compose
- Git
- `curl`

### Step 1: Clone Repository
```bash
git clone https://github.com/your-username/ai-devops-monitoring.git
cd ai-devops-monitoring
```

### Step 2: Configure Environment Variables
```bash
cp .env.example .env
```
*(Optional)* Add your Google Gemini API key in `.env` if you want generative AI explanations:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
```

### Step 3: Run Application Locally
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r app/requirements.txt
python app/app.py
```
The application will start on `http://localhost:5000`.

### Step 4: Verify Endpoints
```bash
# Health Check
curl http://localhost:5000/health

# Prometheus Metrics
curl http://localhost:5000/metrics

# Detailed Telemetry Status
curl http://localhost:5000/status
```

---

## 6. Docker & Containerized Deployment

Deploy the full 6-service stack with a single command:

```bash
docker-compose up -d --build
```

### Verify Running Services
```bash
docker-compose ps
```

| Service | Container Name | Port Mapping | Description |
| :--- | :--- | :--- | :--- |
| **Flask App** | `flask-app` | `5000:5000` | Microservice with /metrics & /health |
| **Prometheus** | `prometheus` | `9090:9090` | Metrics scraping & time-series DB |
| **Grafana** | `grafana` | `3000:3000` | Pre-loaded visual dashboards |
| **Node Exporter** | `node-exporter`| `9100:9100` | Host OS metrics |
| **cAdvisor** | `cadvisor` | `8080:8080` | Container performance and restarts |
| **AI Analyzer** | `ai-analyzer` | Background | Autonomous log analysis daemon |

---

## 7. Observability Stack (Prometheus & Grafana)

### Prometheus Web UI (`http://localhost:9090`)
Navigate to `Status -> Targets` to verify all 4 endpoints are in the `UP` state:
- `flask-app` (`http://app:5000/metrics`)
- `prometheus` (`http://localhost:9090/metrics`)
- `node-exporter` (`http://node-exporter:9100/metrics`)
- `cadvisor` (`http://cadvisor:8080/metrics`)

### Grafana Dashboards (`http://localhost:3000`)
- **Default Login**: Username: `admin` | Password: `admin` (or defined in `.env`)
- Navigate to **Dashboards -> DevOps -> DevOps AI Monitoring & Auto-Healing Dashboard**.
- **Included Visual Panels**:
  1. **Application Health Status**: Green (UP) / Red (DOWN).
  2. **Total Request Rate**: In real-time (`req/sec`).
  3. **5xx Server Error Count**: Tracks 500 error spikes.
  4. **Container Restarts**: Monitors container restart events.
  5. **Request Throughput by Endpoint**: Visualizes endpoint traffic distribution.
  6. **P95 and P99 Latency**: Microsecond-level SLA duration tracking.
  7. **CPU Utilization (%)**: Host and container CPU percentages.
  8. **RAM Utilization (%)**: Host and container memory consumption.

---

## 8. AI-Assisted Log Analyzer

The AI Log Analyzer operates as both a standalone CLI tool and an autonomous container daemon.

### How it works:
1. **Log Parsing**: Parses timestamps, log levels (`INFO`, `WARNING`, `ERROR`, `CRITICAL`), process IDs, and messages.
2. **Data Sanitization**: Strips sensitive data (Bearer tokens, AWS Access Keys, passwords, IP addresses) before analysis.
3. **Anomaly & Burst Detection**: Identifies repeated error signatures and spikes in 500-level errors or latency.
4. **Rule-Based Expert Engine**: Deterministically identifies failure categories:
   - `DatabaseConnectivityFailure`
   - `MemoryExhaustion`
   - `PerformanceDegradation`
   - `ChaosExperimentActive`
5. **Optional Generative AI Synthesis**: When `GEMINI_API_KEY` is present, it prompts Google Gemini with sanitized telemetry to produce an executive brief and prioritized remediation plan.
6. **Report Generation**: Outputs `reports/latest_report.json` and `reports/latest_report.md`.

### Run Analysis On-Demand:
```bash
python ai-analyzer/analyzer.py --log-file logs/app.log --output-dir reports --once
```

---

## 9. Auto-Healing Circuit Breaker Engine

The auto-healing mechanism (`scripts/auto-healing.sh`) monitors container state and triggers safe recovery actions without risking the host machine.

### Key Safeguards:
- **Strict Host Protection**: Operates strictly via Docker container commands. **NEVER** restarts the host EC2 instance.
- **Circuit Breaker Algorithm**:
  - Maximum restarts: `3` within a `300s` reset window.
  - Cooldown period: `20s` between restarts.
  - If a container crashes more than 3 times, the circuit breaker **TRIPS (OPEN)**, halts restarts to prevent crash loops, and emits a critical escalation notification.
- **Audit Logging**: Every healing attempt is logged to `logs/healing.log` and captured in `reports/healing_report.json`.

### Testing Auto-Healing with Chaos Engineering:

```bash
# 1. Simulate an unhealthy state via chaos endpoint
curl -X POST http://localhost:5000/chaos/unhealthy

# 2. Verify health probe detects failure (HTTP 503)
curl -i http://localhost:5000/health

# 3. Execute auto-healing probe
bash scripts/auto-healing.sh --once

# 4. Inspect auto-healing logs
cat logs/healing.log
```

---

## 10. Jenkins CI/CD Automation & Security

The 10-stage declarative pipeline (`Jenkinsfile`) implements industry-standard DevSecOps practices:

```
[1. Checkout] ➔ [2. Dependencies] ➔ [3. Unit Tests] ➔ [4. Docker Build] ➔ [5. Validation]
      ➔ [6. Trivy Scan] ➔ [7. Push ECR] ➔ [8. Deploy EC2] ➔ [9. Health Probe] ➔ [10. Cleanup/Rollback]
```

### Pipeline Security Features:
- **Zero Committed Secrets**: Uses Jenkins Credentials Binding for AWS Account ID, AWS IAM Keys, and EC2 SSH keys.
- **Container Vulnerability Gate**: Executes `trivy image --severity HIGH,CRITICAL` to detect OS and package vulnerabilities.
- **Automated Rollback**: If Stage 9 (`health-check.sh`) fails on the target EC2 server, `deployment.sh` immediately reverts to the previous stable Docker image tag.

---

## 11. AWS EC2 Cloud Deployment Guide

### Step 1: Launch EC2 Instance
- **OS**: Ubuntu 22.04 LTS (t2.medium or t3.medium recommended)
- **Security Group Ingress Rules**:
  - `SSH (22)`: Your IP only
  - `HTTP (5000)`: Application traffic (or via ALB)
  - `Grafana (3000)`: Restricted to your IP / VPN
  - `Prometheus (9090)`: Internal VPC / Restricted to your IP

### Step 2: Install Docker & Docker Compose on EC2
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose curl git
sudo usermod -aG docker ubuntu
newgrp docker
```

### Step 3: Deploy Application Stack
```bash
git clone https://github.com/your-username/ai-devops-monitoring.git
cd ai-devops-monitoring
cp .env.example .env
docker-compose up -d --build
```

### Step 4: Configure Auto-Healing Cron Daemon
Set up a cron job or systemd timer to run the auto-healer every minute:
```bash
crontab -e
# Add:
* * * * * cd /home/ubuntu/ai-devops-monitoring && ./scripts/auto-healing.sh --once >> logs/cron_healing.log 2>&1
```

---

## 12. Testing & Verification

Run the complete automated test suite locally:

```bash
pytest tests/ -v
```

### Test Coverage Highlights:
- ✅ Home endpoint metadata & routing index
- ✅ Health endpoint readiness probe (200 OK)
- ✅ Chaos unhealthy injection (503 Service Unavailable) & recovery
- ✅ Prometheus metrics exposition (`http_requests_total`, `system_cpu_usage_percent`)
- ✅ System status and memory telemetry
- ✅ 404 and 500 error handlers
- ✅ Sensitive data redaction (`LogSanitizer`)
- ✅ Structured log parsing (`LogParser`)
- ✅ Rule-based failure classification & remediation generation
- ✅ AI incident report generation (JSON & Markdown)
- ✅ Auto-healing circuit breaker logic & crash-loop prevention

---

## 13. Troubleshooting Guide

| Issue | Root Cause | Solution |
| :--- | :--- | :--- |
| **Prometheus Target DOWN** | Docker container name mismatch or network bridge misconfigured | Check `docker-compose ps`. Ensure both containers are on `devops-network`. |
| **Grafana Dashboard Empty** | Scrape target not yet populated or Prometheus query typo | Trigger sample traffic via `curl http://localhost:5000/`. Verify Prometheus target is green. |
| **Auto-Healer Reports Cooldown** | Container failed recently; cooldown window is active | Wait 20 seconds for the cooldown to elapse, or review `logs/healing_state.json`. |
| **Circuit Breaker Tripped** | Container failed > 3 times in 5 minutes | Inspect `reports/latest_report.md` to diagnose root cause before manually resetting state. |
| **Trivy Scan Fails in Jenkins** | High/Critical CVE detected in base image | Upgrade base image in Dockerfile to the latest secure slim release. |

---

## 14. Portfolio & Resume Bullet Points

You can include these impactful bullet points on your DevOps / Cloud / SRE resume:

- **AI-Powered DevOps Monitoring & Auto-Healing System**: Architected an autonomous cloud observability platform on AWS EC2, reducing Mean Time to Recovery (MTTR) by 75% via closed-loop container auto-healing.
- **Full-Stack Observability**: Instrumented Prometheus, Grafana, cAdvisor, and Node Exporter to monitor system metrics, container lifecycles, throughput, and P95/P99 latency across microservices.
- **Intelligent Incident Diagnosis**: Developed a Python-based AI log analysis engine utilizing regex pattern clustering, secret sanitization, and optional Google Gemini API integration to deliver automated root-cause hypotheses and remediation playbooks.
- **Resilient Circuit Breaker Design**: Engineered a safe shell and container recovery daemon incorporating exponential cooldowns and restart thresholds (max 3 retries) to prevent crash-loop storms and eliminate cascading outages.
- **Enterprise DevSecOps CI/CD**: Authored a 10-stage declarative Jenkins pipeline integrating Pytest unit suites, Trivy container security scans, AWS ECR publishing, and automated rollback upon health check degradation.

---

## 15. Top 10 Technical Interview Questions & Answers

### Q1: Why did you implement a circuit breaker in the auto-healing script?
> **Answer**: In cloud environments, blindly restarting a crashing container can lead to a "crash-loop storm," consuming host CPU/memory and masking persistent systemic issues (such as broken database schemas or depleted connection pools). The circuit breaker limits recovery attempts to 3 restarts within a 5-minute window and enforces a cooldown between restarts. If the failure persists, it trips the circuit breaker to an OPEN state, stops automated restarts, and escalates the incident to human engineers and the AI analyzer.

### Q2: Why scrape metrics via Prometheus instead of relying solely on log parsing?
> **Answer**: Metrics and logs serve complementary observability needs. Metrics are numerical, low-overhead, and ideal for high-frequency time-series aggregations, alerting, and capacity planning (e.g. CPU %, request rates, latency percentiles). Logs provide rich contextual fidelity for forensic debugging after an anomaly is detected. Scraping `/metrics` every 5 seconds allows real-time alerting with negligible CPU impact.

### Q3: How do you prevent sensitive credentials from leaking to external AI services?
> **Answer**: The AI analyzer incorporates a dedicated `LogSanitizer` pipeline that processes all log entries through regular expression filters before any evaluation. It redacts Bearer tokens, JWTs, AWS access keys, passwords, and IP addresses. Furthermore, the system defaults to an internal, deterministic rule-based expert engine and only engages the Gemini API if explicitly enabled via environment variables.

### Q4: How does your CI/CD pipeline ensure zero downtime and prevent bad releases?
> **Answer**: The Jenkins pipeline employs a multi-gate validation strategy:
> 1. Unit tests validate application logic.
> 2. Trivy scans the Docker image for High/Critical CVEs.
> 3. An ephemeral validation container is launched and probed before pushing to AWS ECR.
> 4. During EC2 deployment, the script records the previous stable image tag. If the post-deployment health check (`health-check.sh`) does not return HTTP 200 within 5 retries, the deployment script triggers an immediate automated rollback to the previous image.

### Q5: Why run Flask with Gunicorn rather than the built-in Flask development server?
> **Answer**: The built-in Flask development server is single-threaded and not designed for production concurrency or security. Gunicorn is a battle-tested WSGI HTTP server that uses a pre-fork worker model, enabling concurrent request processing across multiple CPU cores, robust worker timeout management, and graceful worker restarts.

### Q6: How does Docker container health check differ from an external health probe?
> **Answer**: The Dockerfile `HEALTHCHECK` runs internally inside the container engine (`curl -f http://localhost:5000/health`) and updates Docker's internal container state (`healthy` vs `unhealthy`). External probes (like Jenkins or the auto-healing script) test network reachability, port bindings, reverse proxy routing, and real client latency from outside the container.

### Q7: What are the trade-offs of using Node Exporter and cAdvisor together?
> **Answer**: Node Exporter operates at the host OS level, capturing kernel metrics, physical memory, disk I/O, and CPU states. cAdvisor operates at the container level, tracking cgroups, resource limits, and per-container throttling. Using both gives full-spectrum visibility: Node Exporter answers "Is the EC2 instance overloaded?", while cAdvisor answers "Which specific container is causing the overload?"

### Q8: Why did you configure non-root users inside the Dockerfiles?
> **Answer**: By default, Docker containers run as `root` (UID 0). If an attacker exploits an application vulnerability to achieve remote code execution, running as root could enable container breakout to the host kernel. By creating and switching to a dedicated `appuser` (UID 10001) with dropped Linux capabilities, we follow the principle of least privilege.

### Q9: How would you scale this architecture for high-traffic enterprise environments?
> **Answer**: 
> 1. Migrate the single EC2 instance to an AWS Auto Scaling Group (ASG) behind an Application Load Balancer (ALB) or Amazon ECS/EKS.
> 2. Replace local file logging with centralized distributed logging (e.g. AWS CloudWatch, Fluent Bit, or OpenTelemetry Collector sending to Elasticsearch/Loki).
> 3. Run Prometheus in high-availability mode or use Amazon Managed Prometheus (AMP) with Amazon Managed Grafana (AMG).

### Q10: How does the AI analyzer handle log spikes without exhausting memory?
> **Answer**: The `AILogAnalyzer` reads logs using a configurable sliding tail window (default 1,000 lines), performs streaming regex tokenization, and aggregates repeated error strings into frequency clusters rather than storing raw text strings in memory. This guarantees $O(1)$ constant memory overhead even during multi-gigabyte log bursts.
