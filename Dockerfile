# Repository Analysis System - Docker Configuration
# Multi-stage build for production deployment on zo.computer

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Expose application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.utils.config import ConfigLoader; from src.storage.adapter import create_storage_adapter; config = ConfigLoader().load_config('/app/config/new_config.yaml'); storage = create_storage_adapter(config.get('database', {})); print(storage.health_check())" || exit 1

# Default command
CMD ["python", "scripts/run_graph.py", "--config", "/app/config/new_config.yaml", "analyze"]