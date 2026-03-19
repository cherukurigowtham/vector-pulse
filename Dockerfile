# Stage 1: Builder
FROM python:3.10-slim AS builder

RUN apt-get update && apt-get install -y \
    curl build-essential gcc make \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

ENV PATH="/root/.cargo/bin:${PATH}"
WORKDIR /build

RUN pip install --no-cache-dir maturin

# Copy only Rust build files
COPY Cargo.toml Cargo.lock pyproject.toml ./
COPY src/ ./src/

RUN maturin build --release --out dist

# Stage 2: Runner
FROM python:3.10-slim

# Set working directory to /app
WORKDIR /app

# Set environment variables for Python module discovery
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system runtime dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install runtime dependencies (pre-copy for caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt || true

# Install the pre-built Rust extension
COPY --from=builder /build/dist/*.whl ./dist/
RUN pip install dist/*.whl && rm -rf dist

# Copy the entire application source into /app
COPY . .

# Final check of the structure (debugging only, visible in logs)
RUN ls -la /app/app

# Environment configuration
EXPOSE 8000

# Container Healthcheck (using the new status endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/risk/status || exit 1

# Start the application using module syntax
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
