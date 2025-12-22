# Multi-stage build for optimized Docker image

# Stage 1: Builder
FROM python:3.9-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    musl-dev \
    libssl-dev \
    python3-dev \
    build-essential \
    pkg-config \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip and install build tools
RUN pip install --upgrade pip setuptools wheel

# Create wheel cache directory
WORKDIR /app

# Copy requirements and build wheels
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Final
FROM python:3.9-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    default-libmysqlclient-dev \
    netcat-openbsd \
    curl \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy wheels from builder and install
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/* && rm -rf /wheels

# Copy application code
COPY . .

# Set proper permissions
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Set environment
ENV FLASK_APP=flask_app.py
ENV FLASK_ENV=production

# Entrypoint and CMD
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "flask_app:app"]
