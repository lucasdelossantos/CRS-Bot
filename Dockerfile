# Use Python 3.9 as base (matches minimum version in setup.py)
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install git for potential version checks
RUN apt-get update && \
    apt-get install -y git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r crsbot && useradd -r -g crsbot crsbot

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Install the package in development mode
RUN pip install -e .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Create data directory and set permissions
RUN mkdir -p /app/data && \
    chown -R crsbot:crsbot /app && \
    chmod 755 /app/data

# Create volume for persistent storage
VOLUME ["/app/data"]

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('https://api.github.com/zen')" || exit 1

# Switch to non-root user
USER crsbot

# Run the bot
CMD ["python", "github_release.py"] 