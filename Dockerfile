# Production Dockerfile for CCTV Camera Analyzer
# Optimized for Google Cloud Run / Any container platform

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p gcs_cache sessions analysis_results

# Set environment variables
ENV FLASK_APP=flask_app.py
ENV PYTHONUNBUFFERED=1

# Expose port (Cloud Run uses PORT env variable)
ENV PORT=8080
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# Run the application
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 flask_app:app

