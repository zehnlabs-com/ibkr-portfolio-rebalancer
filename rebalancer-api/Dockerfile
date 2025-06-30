FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and accounts config
COPY app/ ./app/
COPY accounts.yaml ./

# Create non-root user
RUN useradd --create-home --shell /bin/bash rebalancer
USER rebalancer

# Expose port
EXPOSE 8000

# Run the FastAPI application
CMD ["python", "-m", "app.main"]