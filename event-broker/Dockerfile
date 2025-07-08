# Event Broker Service Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and configuration files
COPY app/ ./app/
COPY ../accounts.yaml .
COPY config.yaml .

# Set Python path
ENV PYTHONPATH=/app

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import asyncio; from app.main import app; print('healthy' if asyncio.run(app.get_status()).get('running', False) else 'unhealthy')" || exit 1

# Command to run the application
CMD ["python", "-m", "app.main"]