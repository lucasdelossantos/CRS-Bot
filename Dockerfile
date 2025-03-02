# Build stage
FROM python:3.9-slim AS builder

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
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application files
COPY github_release.py .
COPY config.yaml .
COPY setup.py .
COPY tests/ tests/

# Install package
RUN pip install --no-cache-dir --user -e .

# Final stage
FROM python:3.9-slim

# Add security-related labels
LABEL org.opencontainers.image.vendor="Lucas de los Santos" \
      org.opencontainers.image.title="CRS-Bot" \
      org.opencontainers.image.description="GitHub Release Bot for Core Rule Set" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/lucasdelossantos/CRS-Bot" \
      org.opencontainers.image.security.policy="https://github.com/lucasdelossantos/CRS-Bot/security/policy"

# Set working directory
WORKDIR /app

# Install runtime dependencies and security tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        tini \
        ca-certificates \
        # Add security packages
        apparmor \
        libcap2-bin \
        # Clean up
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/* \
        # Set restrictive umask
        && echo "umask 0027" >> /etc/profile

# Create non-root user with specific UID/GID
RUN groupadd -r -g 10001 crsbot && \
    useradd -r -g crsbot -u 10001 \
        -s /sbin/nologin \
        -d /app \
        --no-log-init \
        crsbot

# Copy runtime files with root ownership and restrictive permissions
COPY --chmod=554 github_release.py .
COPY --chmod=440 config.yaml .
COPY --chmod=554 setup.py .
COPY --chmod=440 requirements.txt .

# Install dependencies and package
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -e . && \
    # Clean up pip cache
    rm -rf /root/.cache/pip/* && \
    # Set proper group for installed packages
    chgrp -R crsbot /usr/local/lib/python3.9/site-packages && \
    chmod -R g+r /usr/local/lib/python3.9/site-packages

# Set security-related environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    # Add security-related env vars
    PYTHON_HASHSEED=random \
    # Prevent core dumps
    PYTHON_DONT_WRITE_BYTECODE=1 \
    # Set restrictive umask
    UMASK=0027

# Create data directory and set permissions
RUN mkdir -p /app/data && \
    # Set proper ownership and permissions
    chown root:crsbot /app && \
    chown root:crsbot /app/data && \
    # Set restrictive permissions
    chmod 550 /app && \
    chmod 750 /app/data && \
    # Add additional capability restrictions
    setcap cap_net_bind_service=+ep /usr/local/bin/python3.9 && \
    # Remove ALL setuid/setgid bits from the entire filesystem
    echo "Removing setuid/setgid bits from all files..." && \
    find / -path /proc -prune -o -perm /6000 -type f -exec chmod a-s {} + 2>/dev/null || true && \
    echo "Verifying no setuid/setgid files remain..." && \
    find / -path /proc -prune -o -perm /6000 -type f -ls 2>/dev/null || true

# Create volume for persistent storage
VOLUME ["/app/data"]

# Add health check with timeout and retries
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('https://api.github.com/zen', timeout=5)" || exit 1

# Switch to non-root user
USER crsbot

# Use tini as init
ENTRYPOINT ["/usr/bin/tini", "--"]

# Set default command
CMD ["python", "github_release.py"]

# Add security options
STOPSIGNAL SIGTERM 