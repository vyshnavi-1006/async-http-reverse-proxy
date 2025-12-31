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
- Temporarily **removes unhealthy backends using a **cooldown mechanism**
- Automatically retries backends after **cooldown expiry**
- Exposes **Prometheus metrics** for observability
- Performs **graceful shutdown with in-flight request draining**
- Logs **requests, retries, failures, latency, and state changes**

---

## How it works

- The proxy receives an incoming HTTP request
- A backend is selected using round-robin scheduling
- The request is forwarded asynchronously to the backend
- The backend response is returned to the client
- If a backend times out or fails:
  - The failure is recorded
  - The request is retried on another backend
- If a backend fails repeatedly:
  - It is marked unhealthy
  - Temporarily skipped using a cooldown timer
- After the cooldown expires:
  - The backend is retried automatically
- Metrics are continuously exposed for monitoring
- On shutdown:
  - New requests are rejected
  - In-flight requests are allowed to complete

---

## Run the project

### 1. Start backend servers

```bash
python -m backends.backend1
python -m backends.backend2
```
### 2. Start the proxy

```bash
python -m proxy
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

Expected behavior:
- Requests are automatically routed to the healthy backend
- Failures and retries are logged
- After repeated failures, the backend is marked unhealthy
- The backend is skipped during the cooldown period
- After cooldown expiry, the proxy retries the backend automatically and ensures continued service.

---

## Graceful shutdown

When the proxy receives a shutdown signal (CTRL+C):
- New requests are rejected with 503 Service Unavailable
- Existing in-flight requests are allowed to complete
- Background tasks are stopped cleanly
- The server exits without dropping active connections
This simulates real-world production shutdown behavior.

---

## Observability & Metrics

The proxy exposes Prometheus metrics on a separate metrics server.
- Metrics endpoint runs on port 8000
- Metrics include:
  - Total requests per backend
  - Failed requests per backend
  - Request latency histograms
  - Python runtime metrics

Example:
```bash
curl http://127.0.0.1:8000
```
These metrics can be scraped by Prometheus and visualized using Grafana.

---

## Logging

- Logs are written to the `logs/` directory when `LOG_DIR=logs` is configured in the `.env` file.
- Separate loggers are maintained for the proxy server and each backend service.
- Logs include:
  - Request IDs
  - Backend selection
  - Timeouts and failures
  - Health state changes
  - Latency measurements
- Log rotation is enabled to prevent uncontrolled log file growth.

---

### Why build this when Nginx / ALB exist?

- To understand how reverse proxies work internally
- To learn async networking with Python
- To implement load balancing, retries, and health checks manually
- To gain hands-on experience with observability and metrics
- To understand graceful shutdown and reliability patterns

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
