# Vector-Pulse: High-Concurrency Fraud Detection Engine

A real-time anomaly detection system built with **Rust** and **Python**, leveraging **Redis** as a feature store. This project demonstrates high-performance systems engineering applied to financial security.

## 🚀 The Architecture


* **Compute Engine (Rust)**: High-performance statistical analysis ($Z$-Score and Velocity math) compiled as a Python extension using `PyO3`.
* **Orchestration (Python)**: Real-time stream processing and decision-making logic.
* **Feature Store (Redis)**: Low-latency persistence for user reputations, sliding windows, and blacklists.
* **Infrastructure (Docker)**: Containerized microservices orchestrated via Docker Compose.

## 📊 Detection Logic
The system evaluates transactions using **Dynamic Thresholding**:
1.  **Statistical Outliers**: Calculates the Moving Average and Standard Deviation ($\sigma$) to determine the $Z$-Score.
    $$Z = \frac{|x - \mu|}{\sigma}$$
2.  **Temporal Velocity**: Detects bot-like behavior by measuring the time-delta between incoming requests.

## 🛠️ Tech Stack
* **Language**: Rust (Performance), Python (Logic)
* **Database**: Redis
* **Tooling**: Docker, Maturin, PyO3

## 🏗️ Local Deployment
```bash
# Build and launch the cluster
docker-compose up --build

# Monitor live Redis keys
docker exec -it [redis-container-id] redis-cli KEYS *
