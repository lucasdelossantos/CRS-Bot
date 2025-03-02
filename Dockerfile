# Use Python 3.9 as base (matches minimum version in setup.py)
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install git for potential version checks
RUN apt-get update && \
    apt-get install -y git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Install the package in development mode
RUN pip install -e .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Create volume for persistent storage
VOLUME ["/app/data"]

# Run the bot
CMD ["python", "github_release.py"] 