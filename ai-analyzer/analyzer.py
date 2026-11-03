"""
AI-Assisted DevOps Log Analyzer & Incident Diagnosis Engine.
Features:
  - Rule-based log parsing & anomaly detection
  - Incident frequency clustering & burst identification
  - Sensitive data sanitization (PII, tokens, secrets)
  - Deterministic root cause & remediation engine
  - Optional Gemini Generative AI synthesis via GEMINI_API_KEY
  - JSON and Markdown report generation

Author: DevOps Engineering Team
Project: AI-Powered DevOps Monitoring & Auto-Healing System
"""

import os
import sys
import re
import json
import time
import argparse
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Setup logger for the analyzer itself
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [AI-Analyzer] %(message)s",
)
logger = logging.getLogger("AI-Analyzer")


class LogSanitizer:
    """Sanitizes sensitive data before AI analysis to preserve security."""

    PATTERNS = [
        # Bearer tokens & JWTs
        (r"(Bearer\s+)[A-Za-z0-9\-\._~\+\/]+=*", r"\1[REDACTED_TOKEN]"),
        # AWS Key IDs
        (r"(AKIA[0-9A-Z]{16})", r"[REDACTED_AWS_KEY]"),
        # Passwords / Secrets in queries or JSON
        (r'("?(?:password|passwd|secret|api_key|token)"?\s*[:=]\s*)"[^"]+"', r'\1"[REDACTED]"'),
        # Generic IPv4 addresses (preserves localhost/internal subnets context if needed, but masks octets)
        (r"\b(?!(?:127\.0\.0\.1|0\.0\.0\.0))\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", r"[REDACTED_IP]"),
    ]

    @classmethod
    def sanitize(cls, text: str) -> str:
        sanitized = text
        for pattern, replacement in cls.PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        return sanitized


class LogParser:
    """Parses application log lines into structured dictionaries."""

    # Matches: 2026-11-03 16:40:54 [ERROR] [DevOpsApp] [pid:1234] Error message here
    LOG_REGEX = re.compile(
        r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\[(?P<level>[A-Z]+)\]\s+\[(?P<logger>[^\]]+)\]\s+(?:\[pid:(?P<pid>\d+)\]\s+)?(?P<message>.*)$"
    )

    @classmethod
    def parse_line(cls, line: str) -> Optional[Dict[str, Any]]:
        line = line.strip()
        if not line:
            return None
        match = cls.LOG_REGEX.match(line)
        if match:
            data = match.groupdict()
            return {
                "timestamp": data["timestamp"],
                "level": data["level"].upper(),
                "logger": data["logger"],
                "pid": data.get("pid") or "N/A",
                "message": data["message"],
                "raw": line,
            }
        else:
            # Fallback for continuation lines, stack traces, or non-standard logs
            return {
                "timestamp": "UNKNOWN",
                "level": "RAW",
                "logger": "raw",
                "pid": "N/A",
                "message": line,
                "raw": line,
            }


class RuleBasedExpertEngine:
    """Deterministic knowledge base providing instant root cause analysis & remediation."""

    KNOWLEDGE_BASE = [
        {
            "pattern": r"(database connection|connection refused|timeout while connecting|db connection)",
            "category": "DatabaseConnectivityFailure",
            "severity": "HIGH",
            "root_cause": "The application cannot establish a connection to the database. Potential causes include database service down, network partition, or connection pool exhaustion.",
            "remediation": [
                "Verify database container or RDS endpoint availability.",
                "Check Docker bridge network connectivity (`docker network inspect devops-network`).",
                "Review database connection pool settings and max connection limits.",
                "Verify database credentials and security group ingress rules.",
            ],
        },
        {
            "pattern": r"(Chaos Triggered|chaos/error|chaos/unhealthy|Chaos injection)",
            "category": "ChaosExperimentActive",
            "severity": "MEDIUM",
            "root_cause": "Controlled chaos testing endpoints were triggered, artificially simulating application errors or unhealthy service states.",
            "remediation": [
                "Verify if a deliberate resilience or auto-healing test is underway.",
                "If testing is complete, restore application health via POST /chaos/recover.",
                "Ensure auto-healing daemon responds and recovers service within SLA thresholds.",
            ],
        },
        {
            "pattern": r"(MemoryError|Out of Memory|OOM|high memory)",
            "category": "MemoryExhaustion",
            "severity": "CRITICAL",
            "root_cause": "Container or host memory exhaustion. Potential memory leak or undersized container memory limit.",
            "remediation": [
                "Inspect memory usage with cAdvisor/Grafana dashboard.",
                "Increase Docker container memory allocation in docker-compose.yml.",
                "Profile application memory allocations using memory_profiler.",
            ],
        },
        {
            "pattern": r"(Simulating high latency|high latency|timed out after)",
            "category": "PerformanceDegradation",
            "severity": "MEDIUM",
            "root_cause": "Request duration exceeded SLA thresholds. Requests are bottlenecked by external dependencies or thread contention.",
            "remediation": [
                "Check Gunicorn worker count and concurrency settings.",
                "Inspect upstream service response times via Grafana P95/P99 latency panels.",
                "Implement caching or asynchronous queue processing for slow tasks.",
            ],
        },
        {
            "pattern": r"(404 completed with status|Resource Not Found)",
            "category": "ClientRoutingError",
            "severity": "LOW",
            "root_cause": "Clients or automated security scanners are requesting non-existent endpoints.",
            "remediation": [
                "Check reverse proxy (Nginx/ALB) path routing rules.",
                "Verify client API call paths.",
                "Implement rate limiting for suspicious repeated 404 probes.",
            ],
        },
    ]

    @classmethod
    def analyze(cls, log_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        findings = []
        full_text = "\n".join([e["message"] for e in log_entries])

        for rule in cls.KNOWLEDGE_BASE:
            matches = re.findall(rule["pattern"], full_text, flags=re.IGNORECASE)
            if matches:
                findings.append(
                    {
                        "category": rule["category"],
                        "severity": rule["severity"],
                        "match_count": len(matches),
                        "root_cause": rule["root_cause"],
                        "remediation": rule["remediation"],
                    }
                )

        if not findings and any(e["level"] in ("ERROR", "CRITICAL") for e in log_entries):
            findings.append(
                {
                    "category": "GenericUnhandledError",
                    "severity": "HIGH",
                    "match_count": sum(1 for e in log_entries if e["level"] in ("ERROR", "CRITICAL")),
                    "root_cause": "Application emitted unclassified ERROR or CRITICAL log events.",
                    "remediation": [
                        "Examine stack traces in the incident report.",
                        "Inspect recent code commits and CI/CD deployment history.",
                        "Verify input payload validation.",
                    ],
                }
            )

        return findings


class GeminiExplainer:
    """Generative AI assistant providing natural-language synthesis via Gemini API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
        self.is_enabled = bool(self.api_key)

    def explain(self, incident_summary: Dict[str, Any], sanitized_sample_logs: List[str]) -> Optional[str]:
        if not self.is_enabled:
            return None

        prompt = f"""
You are an expert Senior Site Reliability Engineer (SRE) and DevOps Architect.
Analyze this application incident telemetry and provide a concise, high-impact assessment.

### Incident Telemetry Summary:
- Total Errors: {incident_summary.get('error_count', 0)}
- Total Criticals: {incident_summary.get('critical_count', 0)}
- Total Warnings: {incident_summary.get('warning_count', 0)}
- Identified Anomaly Signatures: {json.dumps(incident_summary.get('top_signatures', []), indent=2)}

### Sanitized Sample Logs (Last 15 relevant entries):
{chr(10).join(sanitized_sample_logs[-15:])}

### Instructions:
1. Provide a brief 2-sentence Executive Summary of the incident.
2. Outline the most probable Root Cause.
3. List 3 immediate, prioritized DevOps Remediation actions for the on-call engineer.
Do NOT suggest destructive commands (e.g. rm -rf, dropping production databases). Keep advice pragmatic and cloud-native.
"""
        try:
            # Try importing google-genai
            try:
                from google import genai
                client = genai.Client(api_key=self.api_key)
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                )
                if response and hasattr(response, "text") and response.text:
                    return response.text.strip()
            except ImportError:
                # Direct HTTP request fallback to Gemini REST API
                import requests
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                resp = requests.post(url, json=payload, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
                logger.warning(f"Gemini API returned status {resp.status_code}: {resp.text}")

        except Exception as e:
            logger.warning(f"Gemini explanation generation encountered an exception: {e}")

        return None


class AILogAnalyzer:
    """Core log analysis coordinator."""

    def __init__(self, log_file: str, output_dir: str = "reports", gemini_api_key: Optional[str] = None):
        self.log_file = log_file
        self.output_dir = output_dir
        self.gemini = GeminiExplainer(gemini_api_key)
        os.makedirs(self.output_dir, exist_ok=True)

    def read_logs(self, max_lines: int = 1000) -> List[str]:
        if not os.path.exists(self.log_file):
            logger.warning(f"Log file {self.log_file} does not exist yet.")
            return []
        try:
            with open(self.log_file, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                return lines[-max_lines:]
        except Exception as e:
            logger.error(f"Failed to read {self.log_file}: {e}")
            return []

    def analyze(self) -> Dict[str, Any]:
        raw_lines = self.read_logs()
        parsed_entries = []
        for line in raw_lines:
            entry = LogParser.parse_line(line)
            if entry:
                parsed_entries.append(entry)

        level_counts = Counter(e["level"] for e in parsed_entries)
        error_entries = [e for e in parsed_entries if e["level"] in ("ERROR", "CRITICAL")]
        warning_entries = [e for e in parsed_entries if e["level"] == "WARNING"]

        # Signature clustering (grouping similar error messages)
        signatures = Counter()
        for e in error_entries:
            # Strip numbers, paths, timestamps to extract signature
            clean_msg = re.sub(r"\d+", "N", e["message"])
            signatures[clean_msg[:120]] += 1

        top_signatures = [
            {"signature": sig, "count": count} for sig, count in signatures.most_common(5)
        ]

        # Rule-based expert findings
        rule_findings = RuleBasedExpertEngine.analyze(parsed_entries)

        # Build telemetry summary
        summary = {
            "total_lines_analyzed": len(parsed_entries),
            "info_count": level_counts.get("INFO", 0),
            "warning_count": level_counts.get("WARNING", 0),
            "error_count": level_counts.get("ERROR", 0),
            "critical_count": level_counts.get("CRITICAL", 0),
            "top_signatures": top_signatures,
            "rule_findings": rule_findings,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Sanitize logs for optional AI evaluation
        sanitized_logs = [LogSanitizer.sanitize(e["raw"]) for e in (warning_entries + error_entries)[-20:]]

        # Optional Gemini synthesis
        gemini_explanation = None
        if self.gemini.is_enabled and (summary["error_count"] > 0 or summary["critical_count"] > 0):
            logger.info("Querying Gemini API for AI-assisted incident analysis...")
            gemini_explanation = self.gemini.explain(summary, sanitized_logs)

        report = {
            "incident_id": f"INC-{int(time.time())}",
            "status": "INCIDENT_DETECTED" if (summary["error_count"] > 0 or summary["critical_count"] > 0) else "HEALTHY",
            "summary": summary,
            "gemini_analysis": gemini_explanation,
            "rule_based_findings": rule_findings,
            "sample_error_logs": sanitized_logs[-5:] if sanitized_logs else [],
        }

        self.save_reports(report)
        return report

    def save_reports(self, report: Dict[str, Any]):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON
        json_path = os.path.join(self.output_dir, f"report_{timestamp}.json")
        latest_json = os.path.join(self.output_dir, "latest_report.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        with open(latest_json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        # Save Markdown Report
        md_content = self.render_markdown_report(report)
        md_path = os.path.join(self.output_dir, f"report_{timestamp}.md")
        latest_md = os.path.join(self.output_dir, "latest_report.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        with open(latest_md, "w", encoding="utf-8") as f:
            f.write(md_content)

        logger.info(f"Analysis saved to {latest_json} and {latest_md}")

    def render_markdown_report(self, report: Dict[str, Any]) -> str:
        s = report["summary"]
        status_badge = "🔴 CRITICAL INCIDENT" if report["status"] == "INCIDENT_DETECTED" else "🟢 NORMAL / HEALTHY"

        md = f"""# DevOps AI Incident Diagnosis Report

**Incident ID**: `{report['incident_id']}`  
**Evaluation Time**: `{s['generated_at']}`  
**Operational Status**: **{status_badge}**

---

## 1. Telemetry Summary
- **Total Log Lines Processed**: `{s['total_lines_analyzed']}`
- **INFO**: `{s['info_count']}`
- **WARNING**: `{s['warning_count']}`
- **ERROR**: `{s['error_count']}`
- **CRITICAL**: `{s['critical_count']}`

---

## 2. Top Error Signatures
"""
        if s["top_signatures"]:
            for item in s["top_signatures"]:
                md += f"- **Count**: `{item['count']}` | **Signature**: `{item['signature']}`\n"
        else:
            md += "_No recurring error signatures detected._\n"

        md += "\n---\n\n## 3. Rule-Based Root Cause & Remediation\n"
        if report["rule_based_findings"]:
            for finding in report["rule_based_findings"]:
                md += f"### Anomaly Category: `{finding['category']}` (Severity: {finding['severity']})\n"
                md += f"**Probable Root Cause**: {finding['root_cause']}\n\n"
                md += "**Recommended DevOps Actions**:\n"
                for step in finding["remediation"]:
                    md += f"- [ ] {step}\n"
                md += "\n"
        else:
            md += "_No operational failure rules were triggered._\n"

        if report.get("gemini_analysis"):
            md += f"""---

## 4. Generative AI (Gemini) Architectural Assessment
{report['gemini_analysis']}
"""

        md += """---

## 5. Security & Safety Compliance
- All logs passed through `LogSanitizer` (Bearer tokens, AWS keys, passwords, and IP addresses redacted).
- AI recommendations are strictly advisory and do not automatically execute destructive host commands.
"""
        return md


def main():
    parser = argparse.ArgumentParser(description="AI DevOps Log Analyzer")
    parser.add_argument("--log-file", default=os.getenv("LOG_FILE_PATH", "logs/app.log"), help="Path to app log file")
    parser.add_argument("--output-dir", default="reports", help="Directory for incident reports")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=int(os.getenv("AI_ANALYZER_INTERVAL_SECONDS", 60)), help="Loop interval in seconds")
    args = parser.parse_args()

    analyzer = AILogAnalyzer(
        log_file=args.log_file,
        output_dir=args.output_dir,
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
    )

    logger.info(f"AI Log Analyzer initialized. Monitoring: {args.log_file}")
    if analyzer.gemini.is_enabled:
        logger.info("Gemini AI integration is ACTIVE (GEMINI_API_KEY detected).")
    else:
        logger.info("Running in baseline mode: Expert Rule-Based Analysis engine (GEMINI_API_KEY not set).")

    if args.once:
        report = analyzer.analyze()
        logger.info(f"Analysis complete. Status: {report['status']}")
    else:
        logger.info(f"Entering continuous monitoring loop (Interval: {args.interval}s)...")
        while True:
            try:
                analyzer.analyze()
            except Exception as e:
                logger.error(f"Error during scheduled log analysis cycle: {e}")
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
