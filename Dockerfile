# Build stage
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy only requirements first
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY github_release.py .
COPY config.yaml .
COPY setup.py .
COPY tests/ tests/

# Install package
RUN pip install --no-cache-dir -e .

# Test stage
FROM builder AS test
# Install test dependencies
RUN pip install --no-cache-dir pytest pytest-cov
# Set test environment variables
ENV TEST_ENV=true
# Run tests with coverage
RUN python -m pytest tests/ --cov=. --cov-report=term-missing

# Final stage
FROM python:3.11-slim

# Add security-related labels
LABEL org.opencontainers.image.vendor="Lucas de los Santos" \
      org.opencontainers.image.title="CRS-Bot" \
      org.opencontainers.image.description="GitHub Release Bot for Core Rule Set" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/lucasdelossantos/CRS-Bot"

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        tini \
        ca-certificates \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r crsbot && \
    useradd -r -g crsbot \
        -s /sbin/nologin \
        -d /app \
        crsbot

# Copy runtime files
COPY github_release.py .
COPY config.yaml .
COPY setup.py .
COPY requirements.txt .

# Install dependencies and package
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -e . && \
    rm -rf /root/.cache/pip/*

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DOCKER_CONTAINER=1 \
    PYTHON_HASHSEED=random

# Create volumes for persistent storage
VOLUME ["/app/data", "/app/logs"]

# Create data and log directories
RUN mkdir -p /app/data /app/logs && \
    chown -R crsbot:crsbot /app

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('https://api.github.com/zen', timeout=5)" || exit 1

# Switch to non-root user
USER crsbot

# Use tini as init
ENTRYPOINT ["/usr/bin/tini", "--"]

# Set default command
CMD ["python", "github_release.py"] 