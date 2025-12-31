# Custom HTTP Reverse Proxy and Load Balancer

A simple **async reverse proxy** built using **aiohttp** that forwards incoming HTTP requests to multiple backend servers using **round-robin load balancing**.

This project helps to understand how reverse proxies work internally (similar to Nginx / AWS ALB).

---

## What this project does

- Listens for client requests on **port 8080**
- **Forwards requests** to backend servers
- Distributes requests using **round-robin**
- **Retries** on backend failure
- Logs **requests**, **failures**, and **latency**

---

## How it works

- The proxy receives a request
- Selects a backend using round-robin
- Forwards the request to the backend
- Returns the backend response to the client
- If a backend is down, it retries with the next one

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
- Stop one backend server (for example, terminate backend1)
- Continue sending requests:
```bash
curl http://127.0.0.1:8080
```

- The proxy will automatically route requests only to the healthy backend.
- Logs will show backend failure detection and retry behavior.

This demonstrates how the proxy handles backend unavailability and ensures continued service.

---

## Logging

- Logs are written to the `logs/` directory when `LOG_DIR=logs` is configured in the `.env` file.
- Separate loggers are maintained for the proxy server and each backend service.
- Log rotation is enabled to prevent uncontrolled log file growth.

---

### Why build this when Nginx / ALB exist?

- To understand how reverse proxies actually work
- To learn async programming in Python
- To understand load balancing, retries, and failures