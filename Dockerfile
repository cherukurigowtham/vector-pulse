# Use Python 3.10 slim as the base
FROM python:3.10-slim

# Install system dependencies for Rust and C-compilation
RUN apt-get update && apt-get install -y \
    curl build-essential gcc make \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Add Rust to the path
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /app

# Copy Rust package files first (for layer caching)
COPY Cargo.toml Cargo.lock ./
COPY src ./src
COPY pyproject.toml ./

# Copy all Python source files
COPY *.py ./
COPY requirements.txt ./

# Install Python dependencies and build the Rust extension as a wheel
RUN pip install --no-cache-dir -r requirements.txt maturin
RUN maturin build --release --out dist
RUN pip install dist/*.whl

# Expose the API port
EXPOSE 8000

# Container Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start the unified API gateway with multiple workers for concurrency
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
