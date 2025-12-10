# Portuguese Parliament API - Cloud Run compatible Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    'duckdb>=1.1.0' \
    'httpx>=0.27.0' \
    'structlog>=24.4.0' \
    'tenacity>=8.5.0' \
    'fastapi>=0.115.0' \
    'uvicorn[standard]>=0.32.0' \
    'pydantic>=2.9.0' \
    'pydantic-settings>=2.6.0' \
    'python-multipart>=0.0.18'\
    'pytz'

# Copy application code
COPY app/ ./app/
COPY config.py etl/ ./

# Copy data (silver layer Parquet files)
COPY data/silver/ ./data/silver/

# Create non-root user
RUN useradd -m -u 1000 apiuser && \
    chown -R apiuser:apiuser /app
USER apiuser

# Expose port (Cloud Run uses PORT env var, default to 8080)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:${PORT:-8080}/health', timeout=2)"

# Run the application
# Cloud Run sets PORT environment variable
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1
