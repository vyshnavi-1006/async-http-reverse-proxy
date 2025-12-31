import asyncio
import time
import uuid
import os

from aiohttp import web, ClientSession, ClientError, ClientTimeout
from itertools import cycle
from prometheus_client import Counter, Histogram, start_http_server
from dotenv import load_dotenv

from logger import setup_logger

load_dotenv()

logger = setup_logger("proxy")

# METRICS
REQUEST_COUNT = Counter(
    "proxy_requests_total",
    "Total requests",
    ["backend"]
)

REQUEST_FAILED = Counter(
    "proxy_failed_requests_total",
    "Failed requests",
    ["backend"]
)

REQUEST_LATENCY = Histogram(
    "proxy_request_latency_seconds",
    "Request latency in seconds",
    ["backend"]
)

# CONFIG
BACKENDS = [
    os.getenv("BACKEND_1", "http://127.0.0.1:9001"),
    os.getenv("BACKEND_2", "http://127.0.0.1:9002"),
]

PROXY_PORT = int(os.getenv("PROXY_PORT", 8080))

MAX_RETRIES = int(os.getenv("MAX_RETRIES", len(BACKENDS)))

HEALTH_COOLDOWN = int(os.getenv("HEALTH_COOLDOWN", 20))
FAILURE_THRESHOLD = int(os.getenv("FAILURE_THRESHOLD", 3))

TIMEOUT = ClientTimeout(
    total=float(os.getenv("REQUEST_TIMEOUT_TOTAL", 1.5)),
    connect=float(os.getenv("REQUEST_TIMEOUT_CONNECT", 0.5)),
)

# BACKEND STATE
backend_status = {b: True for b in BACKENDS}
backend_cooldown = {b: 0 for b in BACKENDS}
backend_failures = {b: 0 for b in BACKENDS}

backend_pool = cycle(BACKENDS)

# SHUTDOWN STATE
shutting_down = False
in_flight_requests = 0


# PROXY HANDLER
async def proxy_handler(request: web.Request) -> web.Response:
    global in_flight_requests

    if shutting_down:
        return web.Response(
            status=503,
            text="Server is shutting down"
        )

    in_flight_requests += 1

    try:
        request_id = str(uuid.uuid4())
        logger.info(f"[{request_id}] Incoming {request.method} {request.rel_url}")

        start_time = time.perf_counter()
        body = await request.read()

        attempts = 0

        while attempts < MAX_RETRIES:
            backend = next(backend_pool)
            attempts += 1

            # skip unhealthy backend during cooldown
            if not backend_status[backend] and time.time() < backend_cooldown[backend]:
                continue

            target_url = f"{backend}{request.rel_url}"
            logger.info(f"[{request_id}] Attempt {attempts} -> {backend}")

            try:
                async with ClientSession(timeout=TIMEOUT) as session:
                    REQUEST_COUNT.labels(backend=backend).inc()

                    with REQUEST_LATENCY.labels(backend=backend).time():
                        async with session.request(
                            method=request.method,
                            url=target_url,
                            headers=request.headers,
                            data=body,
                        ) as resp:

                            response_body = await resp.read()
                            latency_ms = (time.perf_counter() - start_time) * 1000

                            logger.info(
                                f"[{request_id}] Success | backend={backend} "
                                f"status={resp.status} latency={latency_ms:.2f}ms"
                            )

                            backend_failures[backend] = 0
                            backend_status[backend] = True
                            backend_cooldown[backend] = 0

                            return web.Response(
                                body=response_body,
                                status=resp.status,
                                headers=resp.headers,
                            )

            except asyncio.TimeoutError:
                logger.warning(f"[{request_id}] Timeout from backend {backend}")
                REQUEST_FAILED.labels(backend=backend).inc()
                backend_failures[backend] += 1

            except ClientError as e:
                logger.error(f"[{request_id}] Backend error {backend} | {e}")
                REQUEST_FAILED.labels(backend=backend).inc()
                backend_failures[backend] += 1

            # mark unhealthy if threshold exceeded
            if backend_failures[backend] >= FAILURE_THRESHOLD:
                backend_status[backend] = False
                backend_cooldown[backend] = time.time() + HEALTH_COOLDOWN
                logger.error(f"[{request_id}] Marking backend unhealthy: {backend}")

        latency_ms = (time.perf_counter() - start_time) * 1000
        logger.critical(f"[{request_id}] All backends down | latency={latency_ms:.2f}ms")

        return web.Response(
            status=502,
            text="Bad Gateway: All backend servers are unavailable",
        )

    finally:
        in_flight_requests -= 1


# BACKEND HEALTH MONITOR
async def backend_health_monitor():
    while True:
        now = time.time()
        for backend in BACKENDS:
            if not backend_status[backend] and now >= backend_cooldown[backend]:
                logger.info(f"Cooldown expired, retrying backend: {backend}")
                backend_status[backend] = True
                backend_failures[backend] = 0
                backend_cooldown[backend] = 0
        await asyncio.sleep(5)


# APP LIFECYCLE
async def start_background_tasks(app: web.Application):
    app["health_monitor"] = asyncio.create_task(backend_health_monitor())


async def cleanup_background_tasks(app: web.Application):
    global shutting_down

    logger.info("Shutdown initiated, draining in-flight requests...")
    shutting_down = True

    while in_flight_requests > 0:
        logger.info(f"Waiting for {in_flight_requests} in-flight request(s)")
        await asyncio.sleep(0.5)

    logger.info("All in-flight requests completed")

    app["health_monitor"].cancel()
    await asyncio.sleep(0.1)


# APP SETUP
app = web.Application()
app.router.add_route("*", "/{tail:.*}", proxy_handler)

app.on_startup.append(start_background_tasks)
app.on_cleanup.append(cleanup_background_tasks)


if __name__ == "__main__":
    logger.info(f"Starting proxy server on port {PROXY_PORT}")

    METRICS_PORT = 8000
    start_http_server(METRICS_PORT)
    logger.info(f"Metrics server running on port {METRICS_PORT}")

    web.run_app(app, host="127.0.0.1", port=PROXY_PORT)
