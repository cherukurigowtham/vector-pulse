# Stage 1: Absolute Builder
FROM python:3.10-slim AS builder

RUN apt-get update && apt-get install -y \
    curl build-essential gcc make libpq-dev libffi-dev python3-dev \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

ENV PATH="/root/.cargo/bin:${PATH}"
WORKDIR /build

# 1. Compile all Python dependencies into strict wheel archives instantly
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt

# 2. Build the structural Rust engine into a wheel
RUN pip install --no-cache-dir maturin
COPY Cargo.toml Cargo.lock pyproject.toml ./
COPY src/ ./src/
RUN maturin build --release --out /build/wheels

# ==========================================
# Stage 2: Pure Runner (Zero Compilers)
FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Inject bare runtime linkage for the pre-compiled C-extensions
RUN apt-get update && apt-get install -y curl libpq5 && rm -rf /var/lib/apt/lists/*

# Install all pre-assembled wheels from Stage 1. No network compilation.
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache /wheels/* && rm -rf /wheels

COPY . .

# Final check of the structure
RUN ls -la /app/app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/risk/status || exit 1

CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
