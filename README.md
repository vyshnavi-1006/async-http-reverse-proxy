# Custom HTTP Reverse Proxy and Load Balancer

A production-style async **reverse proxy built using aiohttp** that **forwards incoming HTTP requests to multiple backend servers** using **round-robin load balancing**, with **health checks**, **retries**, **metrics**, and **graceful shutdown**.

This project is designed to understand how reverse proxies work internally (similar to Nginx or AWS ALB) by implementing the core ideas.

---

## What this project does

- Listens for client requests on a **configurable proxy port**
- **Forwards requests** to multiple backend servers
- Distributes traffic using **round-robin load balancing**
- **Retries requests** on backend failure or timeout
- Tracks **backend health status** with failure thresholds
- Temporarily **removes unhealthy backends using a cooldown mechanism**
- Automatically retries backends after **cooldown expiry**
- Performs **graceful shutdown with in-flight request draining**
- Logs **requests, retries, failures, latency, and state changes**
- Exposes **Prometheus-compatible metrics (requests, failures, latency, runtime stats)** on a dedicated metrics endpoint for monitoring and visualization.

---

## Run the project

### 1. Start backend servers

```bash
python -m backends.backend1
python -m backends.backend2
```
### 2. Start the proxy

```bash
python proxy.py
```

### 3. Send requests multiple times
```bash
curl http://127.0.0.1:8080
```
You should see responses alternating between different backends, indicating load balancing.

### 4. Simulate backend failure
- Stop one backend server (for example, backend2)
- Continue sending requests:
```bash
curl http://127.0.0.1:8080
```

---

## Configuration

All configurable values are in the `.env` file:

```env
LOG_DIR=logs
LOG_LEVEL=INFO

PROXY_PORT=8080

BACKEND_1=http://127.0.0.1:9001
BACKEND_2=http://127.0.0.1:9002

MAX_RETRIES=2
FAILURE_THRESHOLD=3
HEALTH_COOLDOWN=20

REQUEST_TIMEOUT_TOTAL=1.5
REQUEST_TIMEOUT_CONNECT=0.5
