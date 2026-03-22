# Stage 1: Go Builder
FROM golang:1.22-alpine AS go-builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o vantix-engine ./cmd/server/main.go

# Stage 2: Python Builder (for ML/DS components if needed)
FROM python:3.10-slim AS py-builder
WORKDIR /build
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt
COPY Cargo.toml Cargo.lock pyproject.toml ./
COPY src/ ./src/
RUN apt-get update && apt-get install -y curl build-essential gcc \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && export PATH="/root/.cargo/bin:${PATH}" \
    && pip install --no-cache-dir maturin \
    && maturin build --release --out /build/wheels

# Stage 3: Sovereign Runner
FROM python:3.10-slim
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y curl libpq5 && rm -rf /var/lib/apt/lists/*

# Copy Go binary
COPY --from=go-builder /app/vantix-engine .

# Copy Python wheels and install (for risk engine processing)
COPY --from=py-builder /build/wheels /wheels
RUN pip install --no-cache /wheels/* && rm -rf /wheels

# Copy source code
COPY . .

EXPOSE 8000
ENV PORT=8000

# Healthcheck hits the Go engine health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Launch the High-Velocity Go Engine
CMD ["./vantix-engine"]
