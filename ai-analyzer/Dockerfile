# =========================================================
# Secure Dockerfile for AI Log Analyzer Daemon
# =========================================================

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LOG_FILE_PATH=/var/log/app/app.log \
    AI_ANALYZER_INTERVAL_SECONDS=30

WORKDIR /analyzer

# Create non-root user
RUN groupadd -g 10002 analyzergroup && \
    useradd -u 10002 -g analyzergroup -s /bin/sh -m analyzeruser

# Install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY analyzer.py .

# Prepare directories
RUN mkdir -p /analyzer/reports /var/log/app && \
    chown -R analyzeruser:analyzergroup /analyzer /var/log/app

USER analyzeruser

CMD ["python", "analyzer.py", "--log-file", "/var/log/app/app.log", "--output-dir", "/analyzer/reports", "--interval", "30"]
