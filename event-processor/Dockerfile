FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (excluding config files)
COPY app/ ./app/
COPY main.py .

# Create non-root user for security
RUN useradd -m -u 1000 trader && chown -R trader:trader /app
USER trader

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV TZ=America/New_York

# Default command
CMD ["python", "main.py"]