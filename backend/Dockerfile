# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Minimal Runtime Image
FROM python:3.12-slim AS runner

WORKDIR /app

# Install minimal runtime library for soundfile and curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Create /data directory for SQLite persistence volume
RUN mkdir -p /data

# Copy application source and test suite
COPY app ./app
COPY tests ./tests

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
